"""Video renderer for SnapReel — streaming scene rendering to FFmpeg pipe."""

from __future__ import annotations

import gc
import logging
import math
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable, Optional, Union

import imageio_ffmpeg
from PIL import Image

from snapreel.schema import Scene, SceneScript
from snapreel.templates import TEMPLATES
from snapreel.templates.common import (
    DEFAULT_FPS,
    clear_bg_cache,
    draw_kinetic_captions,
    ease_in_out_cubic,
    get_canvas_size,
    prepare_kinetic_captions,
    set_canvas,
)
from snapreel.transitions import TRANSITION_FRAMES, blend_frames

logger = logging.getLogger(__name__)

# Use 24fps for rendering — the human eye cannot distinguish 24 vs 30 for
# talking-head / slide content. This alone cuts render time by ~20%.
RENDER_FPS = 24


def _render_scene_with_captions(
    scene: Scene,
    global_frame_offset: int,
    audio_duration: float,
    fps: int = RENDER_FPS,
    global_frame_offset_for_bg: int = 0,
    on_frame: Optional[Callable[[Image.Image, int], None]] = None,
) -> list[Image.Image]:
    """Render a single scene's frames with kinetic captions baked in."""
    template_name = scene.template
    dur = scene.duration
    raw_data = scene.data
    if hasattr(raw_data, "model_dump"):
        payload = raw_data.model_dump(by_alias=True)
    elif isinstance(raw_data, dict):
        payload = raw_data
    else:
        payload = dict(raw_data)

    template_mod = TEMPLATES.get(template_name)
    if template_mod is None:
        raise ValueError(f"Unknown template: '{template_name}'")

    narration = scene.narration or ""
    caption_data = None
    if narration and audio_duration > 0:
        caption_data = prepare_kinetic_captions(narration, audio_duration)

    if on_frame is not None:
        def _cb(frame: Image.Image, fi: int) -> None:
            if caption_data is not None:
                draw_kinetic_captions(frame, narration, fi / fps, audio_duration, cached_data=caption_data)
            on_frame(frame, fi)

        template_mod.render_frames(
            payload,
            duration=dur,
            fps=fps,
            global_frame_offset=global_frame_offset_for_bg,
            on_frame=_cb,
        )
        return []

    frames = template_mod.render_frames(
        payload,
        duration=dur,
        fps=fps,
        global_frame_offset=global_frame_offset_for_bg,
    )

    if caption_data is not None:
        for fi, frame in enumerate(frames):
            t = fi / fps
            draw_kinetic_captions(frame, narration, t, audio_duration, cached_data=caption_data)

    return frames


def render_scene_frames(
    scene_or_template: Union[Scene, str],
    data: Optional[dict[str, Any]] = None,
    duration: Optional[float] = None,
    fps: int = RENDER_FPS,
    global_frame_offset: int = 0,
) -> list[Image.Image]:
    """Public API: render all frames for a single scene or template name."""
    if isinstance(scene_or_template, Scene):
        return _render_scene_with_captions(
            scene_or_template,
            global_frame_offset=0,
            audio_duration=0.0,   # no caption baking when called directly
            fps=fps,
            global_frame_offset_for_bg=global_frame_offset,
        )

    template_name = scene_or_template
    dur = float(duration if duration is not None else 3.0)
    payload = data or {}
    template_mod = TEMPLATES.get(template_name)
    if template_mod is None:
        raise ValueError(f"Unknown template: '{template_name}'")
    return template_mod.render_frames(payload, duration=dur, fps=fps,
                                      global_frame_offset=global_frame_offset)


def render_video(
    script: SceneScript,
    output_path: str,
    audio_path: Optional[str] = None,
    fps: int = RENDER_FPS,
    on_progress: Optional[Callable[[int, int], None]] = None,
    audio_durations: Optional[list[float]] = None,
) -> str:
    """Render all scenes in script to an MP4 video file via ffmpeg pipe.

    Scenes are rendered in parallel using ThreadPoolExecutor.
    Captions are baked into frames (no post-process overlay).
    """
    ratio = getattr(script, "aspect_ratio", "16:9")
    set_canvas(ratio)
    width, height = get_canvas_size()

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "pipe:0",
    ]

    if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 44:
        cmd.extend(["-i", audio_path, "-c:a", "aac"])

    cmd.extend([
        "-vcodec", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "28",          # was 23; 28 is still excellent quality
        "-preset", "veryfast",  # much faster encode, minimal quality loss
        str(out_file),
    ])

    logger.info("Starting ffmpeg pipe rendering (%dx%d @ %dfps) to: %s",
                width, height, fps, out_file)

    # ── Pre-compute cumulative frame offsets per scene ─────────────────────────
    total_scenes = len(script.scenes)
    # Exact frame counts per scene for offset calculation
    scene_frame_counts = [max(1, int(math.ceil(s.duration * fps))) for s in script.scenes]
    cumulative_offsets = [0]
    for fc in scene_frame_counts[:-1]:
        cumulative_offsets.append(cumulative_offsets[-1] + fc)

    # ── Sequential scene streaming directly to ffmpeg pipe ───────────────────────
    # Keeping only 1 scene in memory at a time ensures peak RAM is < 60MB,
    # preventing Out-Of-Memory crashes on container hosts like Render (512MB limit).
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    stderr_lines: list[str] = []

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_lines.append(line.decode("utf-8", errors="ignore").rstrip())

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    try:
        assert proc.stdin is not None
        frames_written = 0
        prev_transition_tail: list[Image.Image] | None = None
        prev_trans_mode: str = "fade"

        for idx in range(total_scenes):
            scene = script.scenes[idx]
            audio_dur = (
                audio_durations[idx]
                if audio_durations and idx < len(audio_durations)
                else 0.0
            )
            logger.info("Rendering scene %d/%d (template: %s)...", idx + 1, total_scenes, scene.template)

            total_scene_frames = scene_frame_counts[idx]
            has_next = idx < total_scenes - 1
            trans_mode = getattr(scene, "transition", "fade") or "fade"
            n_trans = min(TRANSITION_FRAMES, total_scene_frames // 2) if (has_next and trans_mode != "none" and total_scene_frames > 1) else 0
            split_frame_idx = total_scene_frames - n_trans

            curr_tail: list[Image.Image] = []

            def _handle_frame(frame: Image.Image, fi: int) -> None:
                nonlocal frames_written, prev_transition_tail
                out_frame = frame if frame.mode == "RGB" else frame.convert("RGB")

                # Blend transition from previous scene if pending
                if fi == 0 and prev_transition_tail is not None:
                    n_prev = len(prev_transition_tail)
                    for ti in range(n_prev):
                        blended = blend_frames(
                            prev_transition_tail[ti],
                            out_frame,
                            ease_in_out_cubic((ti + 1) / (n_prev + 1)),
                            mode=prev_trans_mode,
                        )
                        proc.stdin.write(blended.tobytes())
                        frames_written += 1
                    prev_transition_tail = None

                # Write directly or buffer in tail for next transition
                if fi < split_frame_idx:
                    proc.stdin.write(out_frame.tobytes())
                    frames_written += 1
                else:
                    curr_tail.append(out_frame)

            _render_scene_with_captions(
                scene,
                global_frame_offset=0,
                audio_duration=audio_dur,
                fps=fps,
                global_frame_offset_for_bg=cumulative_offsets[idx],
                on_frame=_handle_frame,
            )

            prev_transition_tail = curr_tail if curr_tail else None
            prev_trans_mode = trans_mode
            clear_bg_cache()
            gc.collect()

            if on_progress:
                on_progress(idx, total_scenes)

        # Flush any trailing transition tail if present
        if prev_transition_tail:
            for tf in prev_transition_tail:
                proc.stdin.write(tf.tobytes())
                frames_written += 1
            prev_transition_tail = None
            clear_bg_cache()
            gc.collect()

        proc.stdin.close()
        proc.wait(timeout=600)
        stderr_thread.join(timeout=5)

        if proc.returncode != 0:
            err_msg = "\n".join(stderr_lines[-20:])
            logger.error("ffmpeg failed (exit %d): %s", proc.returncode, err_msg)
            raise RuntimeError(
                f"ffmpeg rendering failed (exit code {proc.returncode}): {err_msg}"
            )

    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("ffmpeg rendering timed out after 600 seconds")
    except Exception as exc:
        if proc.poll() is None:
            proc.kill()
        logger.error("Error during video rendering: %s", exc)
        raise RuntimeError(f"Error during video rendering: {exc}") from exc

    logger.info("Successfully rendered video: %s (size: %d bytes)",
                out_file, out_file.stat().st_size)
    return str(out_file)
