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

    Returns RGB PIL Image at the same size with zero float32 memory overhead.
    """
    a_img = frame_a if frame_a.mode == "RGB" else frame_a.convert("RGB")
    b_img = frame_b if frame_b.mode == "RGB" else frame_b.convert("RGB")
    W, H = a_img.size
    t = max(0.0, min(1.0, float(progress)))

    if mode in ("fade", "cross_dissolve"):
        return Image.blend(a_img, b_img, t)

    elif mode == "slide_left":
        # B slides in from right, A slides out to left
        split = int(W * t)
        out = Image.new("RGB", (W, H))
        if split <= 0:
            return a_img.copy()
        elif split >= W:
            return b_img.copy()
        out.paste(a_img.crop((split, 0, W, H)), (0, 0))
        out.paste(b_img.crop((0, 0, split, H)), (W - split, 0))
        return out

    elif mode == "slide_right":
        # B slides in from left, A slides out to right
        split = int(W * t)
        out = Image.new("RGB", (W, H))
        if split <= 0:
            return a_img.copy()
        elif split >= W:
            return b_img.copy()
        out.paste(b_img.crop((W - split, 0, W, H)), (0, 0))
        out.paste(a_img.crop((0, 0, W - split, H)), (split, 0))
        return out

    elif mode == "zoom_in":
        # B scales up from center while A fades out
        scale = 0.85 + 0.15 * t
        new_w = max(1, int(W * scale))
        new_h = max(1, int(H * scale))
        b_scaled = b_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        x0 = max(0, (new_w - W) // 2)
        y0 = max(0, (new_h - H) // 2)
        b_cropped = b_scaled.crop((x0, y0, x0 + W, y0 + H))
        if b_cropped.size != (W, H):
            b_cropped = b_cropped.resize((W, H))
        return Image.blend(a_img, b_cropped, t)

    else:  # "none"
        return b_img if t >= 0.5 else a_img


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
