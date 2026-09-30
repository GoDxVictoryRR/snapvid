"""Text-to-speech (TTS) synthesis, caption alignment, and duration reconciliation.

Supports Kokoro TTS, Edge TTS, and Windows SAPI fallback.
Includes narrate-first preparation, duration reconciliation, audio concat, and caption rendering.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import os
from pathlib import Path
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional
import wave

import numpy as np
from PIL import Image, ImageDraw

from snapreel.schema import Scene, SceneScript
from snapreel.templates.common import (
    PALETTE,
    SIZES,
    draw_text_shadowed,
    get_canvas_ratio,
    get_canvas_size,
    hex_to_rgba,
    load_font,
    wrap_text,
)

logger = logging.getLogger(__name__)


def _narrate_kokoro(text: str, output_wav: str, voice: str = "af_heart") -> float:
    from kokoro import KPipeline  # type: ignore
    import soundfile as sf  # type: ignore

    out_path = Path(output_wav).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code="a")
    samples = []
    sample_rate = 24000
    for _, _, audio in pipeline(text, voice=voice, speed=1.1):
        samples.append(audio)
    combined = np.concatenate(samples) if samples else np.zeros(sample_rate)
    sf.write(str(out_path), combined, sample_rate)
    return float(len(combined) / sample_rate)


async def _narrate_edge_async(text: str, output_wav: str, voice: str = "en-US-AriaNeural") -> float:
    import edge_tts  # type: ignore
    import imageio_ffmpeg  # type: ignore

    out_path = Path(output_wav).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp3 = str(out_path.with_suffix(".tmp.mp3"))

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(tmp_mp3)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-i", tmp_mp3, str(out_path)], check=True, capture_output=True)
    if os.path.exists(tmp_mp3):
        os.remove(tmp_mp3)

    with wave.open(str(out_path), "rb") as wf:
        rate = wf.getframerate()
        return wf.getnframes() / float(rate) if rate > 0 else 0.0


def _narrate_edge(text: str, output_wav: str, voice: str = "en-US-AriaNeural") -> float:
    return asyncio.run(_narrate_edge_async(text, output_wav, voice))


def _narrate_sapi(text: str, output_wav: str) -> float:
    if platform.system() != "Windows":
        raise RuntimeError("TTS only supported on Windows")

    clean_text = text.strip()
    out_path = Path(output_wav).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError(f"pywin32 is required for Windows SAPI TTS: {exc}") from exc

    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Open(str(out_path), 3)  # SSFMCreateForWrite
        speaker.AudioOutputStream = stream
        speaker.Speak(clean_text)
        stream.Close()
    except Exception as exc:
        logger.error("Failed to synthesize speech with SAPI: %s", exc)
        raise RuntimeError(f"TTS synthesis failed: {exc}") from exc

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(f"TTS audio output was not generated at: {out_path}")

    try:
        with wave.open(str(out_path), "rb") as wf:
            rate = wf.getframerate()
            return wf.getnframes() / float(rate) if rate > 0 else 0.0
    except Exception as exc:
        logger.warning("Could not read WAV duration via wave stdlib: %s", exc)
        return 0.0


def narrate(text: str, output_wav: str, engine: str = "auto", voice: str = "auto") -> float:
    """Synthesize text using auto-selected or specified engine."""
    if engine == "auto":
        engine = os.environ.get("TTS_ENGINE", "auto")
    if voice == "auto":
        voice = os.environ.get("TTS_VOICE", "auto")

    engines = ["kokoro", "edge", "sapi"] if engine == "auto" else [engine]

    last_error: Optional[Exception] = None
    for eng in engines:
        try:
            if eng == "kokoro":
                v = "af_heart" if voice == "auto" else voice
                return _narrate_kokoro(text, output_wav, voice=v)
            elif eng == "edge":
                v = "en-US-AriaNeural" if voice == "auto" else voice
                return _narrate_edge(text, output_wav, voice=v)
            elif eng == "sapi":
                return _narrate_sapi(text, output_wav)
            else:
                raise ValueError(f"Unknown TTS engine: {eng}")
        except Exception as exc:
            last_error = exc
            logger.warning("TTS engine %s failed: %s, trying next...", eng, exc)

    if last_error and "TTS only supported on Windows" in str(last_error):
        raise RuntimeError("TTS only supported on Windows")
    raise RuntimeError(f"All TTS engines failed: {last_error}")


def prepare_audio(
    script: SceneScript,
    tmp_dir: str,
    engine: str = "auto",
    voice: str = "auto",
) -> tuple[list[str], list[float]]:
    """Synthesize narration for all scenes in parallel. Returns (wav_paths, durations)."""
    n_scenes = len(script.scenes)
    wav_paths: list[str] = [""] * n_scenes
    durations: list[float] = [0.0] * n_scenes

    tasks = []
    for idx, scene in enumerate(script.scenes):
        if scene.narration and scene.narration.strip():
            path = os.path.join(tmp_dir, f"{scene.id}.wav")
            tasks.append((idx, scene.narration, path))

    if not tasks:
        return wav_paths, durations

    def _worker(item: tuple[int, str, str]) -> tuple[int, str, float]:
        idx, text, out_p = item
        d = narrate(text, out_p, engine=engine, voice=voice)
        return idx, out_p, d

    max_workers = min(len(tasks), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_worker, t) for t in tasks]
        for fut in as_completed(futures):
            idx, out_p, d = fut.result()
            wav_paths[idx] = out_p
            durations[idx] = d

    return wav_paths, durations


def reconcile_durations(
    script: SceneScript,
    audio_durations: list[float],
    min_tail_padding: float = 0.3,
    max_trailing_pause: float = 2.0,
    target_duration: Optional[float] = None,
) -> SceneScript:
    """Adjust scene durations so audio is never clipped and target video length is accurately achieved."""
    new_script = copy.deepcopy(script)

    # Standard path: when target_duration is not requested, use natural padding
    if target_duration is None or target_duration <= 0:
        for i, scene in enumerate(new_script.scenes):
            audio_dur = audio_durations[i] if i < len(audio_durations) else 0.0
            if audio_dur > 0:
                min_dur = audio_dur + min_tail_padding
                natural_max = audio_dur + max_trailing_pause
                if scene.duration > natural_max:
                    scene.duration = round(natural_max, 2)
                else:
                    scene.duration = round(max(scene.duration, min_dur), 2)
            else:
                scene.duration = round(scene.duration, 2)
        new_script.total_duration = round(sum(s.duration for s in new_script.scenes), 2)
        return new_script

    # Target-duration aware path: guarantee video hits selected duration across all presets
    n = len(new_script.scenes)
    min_safes: list[float] = []
    for i, scene in enumerate(new_script.scenes):
        audio_dur = audio_durations[i] if i < len(audio_durations) else 0.0
        if audio_dur > 0:
            min_safes.append(audio_dur + min_tail_padding)
        else:
            min_safes.append(max(2.5, scene.duration))

    total_min_safe = sum(min_safes)

    if total_min_safe >= target_duration:
        # Audio narration alone fills or exceeds target duration: keep audio unclipped
        for i, scene in enumerate(new_script.scenes):
            scene.duration = round(min_safes[i], 2)
    else:
        # Extra duration available: distribute proportionally across scenes so video hits target duration
        extra_time = target_duration - total_min_safe
        for i, scene in enumerate(new_script.scenes):
            weight = min_safes[i] / total_min_safe if total_min_safe > 0 else 1.0 / max(1, n)
            added = extra_time * weight
            scene.duration = round(min_safes[i] + added, 2)

    # Adjust rounding differences on final scene so sum matches target_duration exactly
    if new_script.scenes and total_min_safe < target_duration:
        actual_sum = sum(s.duration for s in new_script.scenes)
        diff = round(target_duration - actual_sum, 2)
        if abs(diff) > 0.001:
            new_script.scenes[-1].duration = round(max(min_safes[-1], new_script.scenes[-1].duration + diff), 2)

    new_script.total_duration = round(sum(s.duration for s in new_script.scenes), 2)
    return new_script


def concat_audio(
    wav_paths: list[str],
    scene_durations: list[float],
    output_wav: str,
    sample_rate: int = 22050,
) -> str:
    """Concatenate per-scene WAVs with silence padding to fill scene durations."""
    frames_all = bytearray()
    channels, sampwidth = 1, 2

    for path, dur in zip(wav_paths, scene_durations):
        audio_dur = 0.0
        if path and os.path.exists(path) and os.path.getsize(path) > 44:
            try:
                with wave.open(path, "rb") as wf:
                    sr = wf.getframerate()
                    ch = wf.getnchannels()
                    raw = wf.readframes(wf.getnframes())

                    if ch == 2:
                        samples = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2)
                        raw = samples.mean(axis=1).astype(np.int16).tobytes()

                    if sr != sample_rate:
                        samples = np.frombuffer(raw, dtype=np.int16)
                        new_len = int(len(samples) * sample_rate / sr)
                        if new_len > 0:
                            idx = np.linspace(0, len(samples) - 1, new_len)
                            raw = np.interp(idx, np.arange(len(samples)), samples).astype(np.int16).tobytes()

                    frames_all += raw
                    audio_dur = len(raw) / (sampwidth * sample_rate)
            except Exception as e:
                logger.warning("Error reading wav %s: %s", path, e)
                audio_dur = 0.0

        silence_dur = max(0.0, dur - audio_dur)
        silence_samples = int(round(silence_dur * sample_rate))
        frames_all += b'\x00' * silence_samples * sampwidth

    out_path = Path(output_wav).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames_all))
    return str(out_path)


def build_captions(
    scenes: list[Scene],
    audio_durations: Optional[list[float]] = None,
) -> list[dict[str, Any]]:
    """Build caption list with cumulative start and end timestamps matching video frames."""
    captions = []
    current_time = 0.0
    for i, scene in enumerate(scenes):
        scene_dur = float(scene.duration)
        if audio_durations and i < len(audio_durations) and audio_durations[i] > 0:
            active_dur = min(scene_dur, float(audio_durations[i]) + 0.3)
        else:
            active_dur = scene_dur

        start = round(current_time, 3)
        end = round(current_time + active_dur, 3)
        captions.append({
            "scene_id": scene.id,
            "start_sec": start,
            "end_sec": end,
            "text": scene.narration or "",
        })
        current_time += scene_dur
    return captions


def get_caption_at_time(captions: list[dict[str, Any]], t: float) -> str | None:
    """Return narration text active at global time t, or None."""
    for cap in captions:
        if cap["start_sec"] <= t < cap["end_sec"]:
            return cap.get("text")
    return None


def draw_caption_overlay(canvas: Image.Image, text: str, style: str = "pill") -> None:
    """Render subtitle text at bottom of canvas in-place."""
    if not text or not text.strip():
        return
    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    caption_size = 20 if ratio == "9:16" else SIZES["caption"]
    font = load_font(bold=False, size=caption_size)
    lines = wrap_text(text.strip(), font, min(w - 80, 1100))
    if not lines:
        return

    dummy = Image.new("RGBA", (1, 1))
    ddraw = ImageDraw.Draw(dummy)
    bboxes = [ddraw.textbbox((0, 0), l, font=font) for l in lines]
    max_line_w = int(max(b[2] - b[0] for b in bboxes))
    line_h = int(max(b[3] - b[1] for b in bboxes) + 6)
    total_h = len(lines) * line_h

    center_x = w // 2
    bottom_y = h - 60 - total_h

    if style == "pill":
        pw = max_line_w + 48
        ph = total_h + 20
        px = center_x - (pw // 2)
        py = bottom_y - 10
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.rounded_rectangle([px, py, px + pw, py + ph], radius=min(22, ph // 2), fill=(0, 0, 0, 180))
        canvas.alpha_composite(overlay)

    draw = ImageDraw.Draw(canvas)
    for i, line in enumerate(lines):
        tb = ddraw.textbbox((0, 0), line, font=font)
        lw = int(tb[2] - tb[0])
        lx = center_x - (lw // 2)
        ly = bottom_y + i * line_h
        draw_text_shadowed(draw, (lx, ly), line, font, hex_to_rgba(PALETTE["text_hi"], 1.0), (0, 0, 0, 180), offset=(2, 2))


__all__ = [
    "narrate", "prepare_audio", "reconcile_durations", "concat_audio",
    "build_captions", "get_caption_at_time", "draw_caption_overlay",
    "_narrate_kokoro", "_narrate_edge", "_narrate_sapi",
]
