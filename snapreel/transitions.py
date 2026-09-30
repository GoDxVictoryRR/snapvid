"""Scene transition system for SnapReel.

Pure numpy frame blending supporting fade, cross_dissolve, slide_left,
slide_right, zoom_in, and none.
"""

from __future__ import annotations

from typing import Iterator
import numpy as np
from PIL import Image

from snapreel.templates.common import ease_in_out_cubic

TRANSITION_FRAMES = 10      # 10 frames = ~0.4s transition at 24fps
TRANSITION_FPS_COST = 10    # transition frame count


def blend_frames(
    frame_a: Image.Image,
    frame_b: Image.Image,
    progress: float,
    mode: str = "fade",
) -> Image.Image:
    """Composite frame_a and frame_b at given progress for the named transition.

    Returns RGB PIL Image at the same size.
    """
    a_img = frame_a.convert("RGB")
    b_img = frame_b.convert("RGB")
    a = np.array(a_img, dtype=np.float32)
    b = np.array(b_img, dtype=np.float32)
    H, W = a.shape[:2]
    t = float(np.clip(progress, 0.0, 1.0))

    if mode in ("fade", "cross_dissolve"):
        out = a * (1.0 - t) + b * t

    elif mode == "slide_left":
        # B slides in from right, A slides out to left
        split = int(W * t)
        out = a.copy()
        if split > 0:
            out[:, :W - split, :] = a[:, split:, :]
            out[:, W - split:, :] = b[:, :split, :]

    elif mode == "slide_right":
        # B slides in from left, A slides out to right
        split = int(W * t)
        out = a.copy()
        if split > 0:
            out[:, split:, :] = a[:, :W - split, :]
            out[:, :split, :] = b[:, W - split:, :]

    elif mode == "zoom_in":
        # B scales up from center while A fades out
        scale = 0.85 + 0.15 * t
        new_w = max(1, int(W * scale))
        new_h = max(1, int(H * scale))
        b_scaled = np.array(
            Image.fromarray(b.astype(np.uint8)).resize((new_w, new_h), Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
        x0 = max(0, (new_w - W) // 2)
        y0 = max(0, (new_h - H) // 2)
        b_cropped = b_scaled[y0:y0 + H, x0:x0 + W, :]
        if b_cropped.shape[:2] != (H, W):
            b_cropped = np.array(
                Image.fromarray(b_scaled.astype(np.uint8)).resize((W, H)),
                dtype=np.float32,
            )
        out = a * (1.0 - t) + b_cropped * t

    else:  # "none"
        out = b if t >= 0.5 else a

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def generate_transition(
    last_frame: Image.Image,
    first_frame: Image.Image,
    mode: str = "fade",
    n_frames: int = TRANSITION_FRAMES,
) -> Iterator[Image.Image]:
    """Yield n_frames blended transition frames between two scenes."""
    for i in range(n_frames):
        raw_t = (i + 1) / (n_frames + 1)
        t = ease_in_out_cubic(raw_t)
        yield blend_frames(last_frame, first_frame, t, mode)


__all__ = [
    "TRANSITION_FRAMES",
    "TRANSITION_FPS_COST",
    "blend_frames",
    "generate_transition",
]
