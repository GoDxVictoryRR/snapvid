"""Video renderer for SnapReel — optimized with parallel scene rendering.

Key changes vs previous version:
- ThreadPoolExecutor renders scenes in parallel (major speedup)
- 24 fps default (was 30) — imperceptible quality loss, 20% fewer frames
- Kinetic captions baked INTO frames during render (not as post-process overlay)
- Old draw_caption_overlay pill-box removed entirely
- CRF 28 (was 23) — slightly smaller file, still visually excellent
"""

from __future__ import annotations

import logging
import os
import math
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Optional, Union

import imageio_ffmpeg
from PIL import Image

from snapreel.schema import Scene, SceneScript
from snapreel.templates import TEMPLATES
from snapreel.templates.common import (
    DEFAULT_FPS,
    draw_kinetic_captions,
    prepare_kinetic_captions,
    get_canvas_size,
    set_canvas,
    ease_in_out_cubic,
)
from snapreel.transitions import (
    TRANSITION_FRAMES,
    blend_frames,
    generate_transition,
)
from snapreel.tts import build_captions, get_caption_at_time

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

    frames = template_mod.render_frames(
        payload,
        duration=dur,
        fps=fps,
        global_frame_offset=global_frame_offset_for_bg,
    )

    # Bake kinetic captions directly onto each frame
    narration = scene.narration or ""
    if narration and audio_duration > 0:
        caption_data = prepare_kinetic_captions(narration, audio_duration)
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

    # ── Parallel scene rendering ───────────────────────────────────────────────
    logger.info("Rendering %d scenes in parallel...", total_scenes)
    scene_frames: dict[int, list[Image.Image]] = {}

    def _render_idx(idx: int) -> tuple[int, list[Image.Image]]:
        scene = script.scenes[idx]
        audio_dur = (audio_durations[idx] if audio_durations and idx < len(audio_durations)
                     else 0.0)
        frames = _render_scene_with_captions(
            scene,
            global_frame_offset=0,
            audio_duration=audio_dur,
            fps=fps,
            global_frame_offset_for_bg=cumulative_offsets[idx],
        )
        return idx, frames

    # Use min(scenes, 4) workers — more than 4 rarely helps due to GIL + memory
    max_workers = min(total_scenes, 4)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_render_idx, i): i for i in range(total_scenes)}
        completed = 0
        for fut in as_completed(futures):
            idx, frames = fut.result()
            scene_frames[idx] = frames
            completed += 1
            logger.info("Scene %d/%d rendered (%d frames)", completed, total_scenes, len(frames))

    # ── ffmpeg pipe ────────────────────────────────────────────────────────────
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

        curr_frames = scene_frames[0] if total_scenes > 0 else []

        for idx in range(total_scenes):
            has_next = idx < total_scenes - 1

            if has_next:
                next_frames = scene_frames[idx + 1]
                trans_mode = getattr(script.scenes[idx], "transition", "fade") or "fade"
                if trans_mode != "none" and len(curr_frames) > 1 and len(next_frames) > 0:
                    n_trans = min(TRANSITION_FRAMES, len(curr_frames) // 2)
                    direct_frames = curr_frames[:-n_trans]
                    trans_frames = [
                        blend_frames(
                            curr_frames[len(curr_frames) - n_trans + i],
                            next_frames[0],
                            ease_in_out_cubic((i + 1) / (n_trans + 1)),
                            mode=trans_mode,
                        )
                        for i in range(n_trans)
                    ]
                else:
                    direct_frames = curr_frames
                    trans_frames = []
            else:
                direct_frames = curr_frames
                trans_frames = []
                next_frames = []

            for frame in direct_frames:
                out_frame = frame if frame.mode == "RGB" else frame.convert("RGB")
                proc.stdin.write(out_frame.tobytes())
                frames_written += 1

            for frame in trans_frames:
                out_frame = frame if frame.mode == "RGB" else frame.convert("RGB")
                proc.stdin.write(out_frame.tobytes())
                frames_written += 1

            if on_progress:
                on_progress(idx, total_scenes)

            curr_frames = next_frames

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
