"""Video renderer for SnapReel.

Renders scenes into RGB frames via PIL templates and pipes them directly to ffmpeg.
Outputs 1280x720 @ 30fps H.264 MP4 videos.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional, Union

import imageio_ffmpeg
from PIL import Image

from snapreel.schema import Scene, SceneScript
from snapreel.templates import TEMPLATES
from snapreel.templates.common import DEFAULT_FPS, HEIGHT, WIDTH

logger = logging.getLogger(__name__)


def render_scene_frames(
    scene_or_template: Union[Scene, str],
    data: Optional[dict[str, Any]] = None,
    duration: Optional[float] = None,
    fps: int = DEFAULT_FPS,
) -> list[Image.Image]:
    """Render all frames for a single scene or template name.

    Args:
        scene_or_template: Scene instance or string template name.
        data: Optional dictionary of data if scene_or_template is a string.
        duration: Optional duration in seconds if scene_or_template is a string.
        fps: Frames per second (default 30).

    Returns:
        List of PIL Images in RGB format.

    Raises:
        ValueError: If template name is unrecognized.
    """
    if isinstance(scene_or_template, Scene):
        template_name = scene_or_template.template
        dur = scene_or_template.duration
        raw_data = scene_or_template.data
        if hasattr(raw_data, "model_dump"):
            payload = raw_data.model_dump(by_alias=True)
        elif isinstance(raw_data, dict):
            payload = raw_data
        else:
            payload = dict(raw_data)
    else:
        template_name = str(scene_or_template)
        dur = float(duration if duration is not None else 3.0)
        payload = data or {}

    template_mod = TEMPLATES.get(template_name)
    if template_mod is None:
        raise ValueError(f"Unknown template: '{template_name}'")

    return template_mod.render_frames(payload, duration=dur, fps=fps)


def render_video(
    script: SceneScript,
    output_path: str,
    audio_path: Optional[str] = None,
    fps: int = DEFAULT_FPS,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> str:
    """Render all scenes in script to an MP4 video file via ffmpeg pipe.

    Args:
        script: Validated SceneScript containing scene definitions.
        output_path: Target path for the output MP4 file.
        audio_path: Optional path to an audio track (e.g. TTS WAV).
        fps: Frames per second (default 30).
        on_progress: Optional callback func(scene_idx, total_scenes).

    Returns:
        Resolved output_path string.

    Raises:
        RuntimeError: If ffmpeg subprocess fails or fails to write frames.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "pipe:0",
    ]

    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-shortest"])

    cmd.extend([
        "-vcodec", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        str(out_file),
    ])

    logger.info("Starting ffmpeg pipe rendering to: %s", out_file)
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    total_scenes = len(script.scenes)

    try:
        assert proc.stdin is not None
        for idx, scene in enumerate(script.scenes):
            logger.info("Rendering scene %d/%d (%s)", idx + 1, total_scenes, scene.template)
            frames = render_scene_frames(scene, fps=fps)

            for frame in frames:
                if frame.mode != "RGB":
                    frame = frame.convert("RGB")
                proc.stdin.write(frame.tobytes())

            if on_progress:
                on_progress(idx, total_scenes)

        proc.stdin.close()
        stdout_data, stderr_data = proc.communicate()

        if proc.returncode != 0:
            err_msg = stderr_data.decode("utf-8", errors="ignore")
            logger.error("ffmpeg failed with return code %d: %s", proc.returncode, err_msg)
            raise RuntimeError(f"ffmpeg rendering failed (exit code {proc.returncode}): {err_msg}")

    except Exception as exc:
        if proc.poll() is None:
            proc.kill()
        logger.error("Error during video rendering: %s", exc)
        raise RuntimeError(f"Error during video rendering: {exc}") from exc

    logger.info("Successfully rendered video: %s (size: %d bytes)", out_file, out_file.stat().st_size)
    return str(out_file)


__all__ = [
    "render_scene_frames",
    "render_video",
]
