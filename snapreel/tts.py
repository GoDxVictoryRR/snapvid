"""Text-to-speech (TTS) synthesis and caption alignment for SnapReel.

Supports multiple voice engines with automatic selection:
1. Kokoro TTS (offline, high quality neural)
2. Edge TTS (online, Microsoft neural voices)
3. Windows SAPI (offline fallback for Windows)
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import platform
import subprocess
from typing import Any, Optional
import wave

from snapreel.schema import Scene

logger = logging.getLogger(__name__)


def _narrate_kokoro(text: str, output_wav: str, voice: str = "af_heart") -> float:
    """Synthesize speech using Kokoro TTS."""
    from kokoro import KPipeline
    import soundfile as sf
    import numpy as np

    out_path = Path(output_wav).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code="a")  # "a" = American English
    samples = []
    sample_rate = 24000
    for _, _, audio in pipeline(text, voice=voice, speed=1.1):
        samples.append(audio)
    combined = np.concatenate(samples) if samples else np.zeros(sample_rate)
    sf.write(str(out_path), combined, sample_rate)
    return float(len(combined) / sample_rate)


async def _narrate_edge_async(text: str, output_wav: str, voice: str = "en-US-AriaNeural") -> float:
    """Asynchronously synthesize speech using Edge TTS."""
    import edge_tts
    import imageio_ffmpeg

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
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate) if rate > 0 else 0.0


def _narrate_edge(text: str, output_wav: str, voice: str = "en-US-AriaNeural") -> float:
    """Synchronously synthesize speech using Edge TTS."""
    return asyncio.run(_narrate_edge_async(text, output_wav, voice))


def _narrate_sapi(text: str, output_wav: str) -> float:
    """Synthesize speech using Windows built-in SAPI."""
    if platform.system() != "Windows":
        raise RuntimeError("TTS only supported on Windows")

    clean_text = text.strip()
    out_path = Path(output_wav).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(f"pywin32 is required for Windows SAPI TTS: {exc}") from exc

    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        # 3 = SSFMCreateForWrite
        stream.Open(str(out_path), 3)
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
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate) if rate > 0 else 0.0
    except Exception as exc:
        logger.warning("Could not read WAV duration via wave stdlib: %s", exc)
        return 0.0


def narrate(text: str, output_wav: str, engine: str = "auto", voice: str = "auto") -> float:
    """Synthesize text to output_wav using auto-selected or specified engine.

    Args:
        text: Narration script to speak.
        output_wav: Path to destination WAV file.
        engine: "auto" | "kokoro" | "edge" | "sapi"
        voice: Voice identifier or "auto" for engine default.

    Returns:
        Actual audio duration in seconds.

    Raises:
        RuntimeError: If all selected engines fail to synthesize speech.
    """
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


def build_captions(
    scenes: list[Scene],
    audio_durations: Optional[list[float]] = None,
) -> list[dict[str, Any]]:
    """Build caption list with cumulative start and end timestamps.

    Args:
        scenes: List of Scene definitions.
        audio_durations: List of audio durations in seconds per scene. If omitted
            or shorter than scenes count, falls back to scene.duration.

    Returns:
        List of dicts: {"scene_id": str, "start_sec": float, "end_sec": float, "text": str}.
    """
    captions = []
    current_time = 0.0

    for i, scene in enumerate(scenes):
        if audio_durations is not None and i < len(audio_durations):
            dur = max(0.0, float(audio_durations[i]))
        else:
            dur = max(0.0, float(scene.duration))

        start = round(current_time, 3)
        end = round(current_time + dur, 3)

        captions.append({
            "scene_id": scene.id,
            "start_sec": start,
            "end_sec": end,
            "text": scene.narration or "",
        })
        current_time += dur

    return captions


__all__ = [
    "narrate",
    "build_captions",
    "_narrate_kokoro",
    "_narrate_edge",
    "_narrate_sapi",
]
