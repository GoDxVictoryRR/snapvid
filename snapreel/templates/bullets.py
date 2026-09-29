"""Bullet list scene template renderer."""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    create_canvas,
    ease_out_cubic,
    hex_to_rgba,
    load_font,
)


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS) -> list[Image.Image]:
    """Render bullet reveal frames with staggered fade-in animations.

    Args:
        data: Template data containing 'heading' and 'items' list.
        duration: Duration of the scene in seconds.
        fps: Frames per second (default 30).

    Returns:
        List of RGB PIL Images.
    """
    total_frames = max(1, int(math.ceil(duration * fps)))
    heading_text = str(data.get("heading", ""))
    raw_items = data.get("items", [])
    # Max 6 bullets, clip if more
    items = [str(item) for item in raw_items[:6]]

    font_heading = load_font(bold=True, size=56)
    font_bullet = load_font(bold=False, size=36)

    margin_x = 80
    heading_y = 120
    bullets_start_y = 240
    row_height = 64
    dot_radius = 5

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = create_canvas()
        draw = ImageDraw.Draw(canvas)

        # Animate heading (fade-in over first 0.4s)
        h_p = min(1.0, t / 0.4) if duration > 0 else 1.0
        h_e = ease_out_cubic(h_p)
        draw.text(
            (margin_x, heading_y),
            heading_text,
            fill=hex_to_rgba("#ffffff", h_e),
            font=font_heading,
        )

        # Render bullet items staggered: item i appears at t = 0.3 * i seconds
        for i, item_text in enumerate(items):
            item_start_t = 0.3 * i
            if t < item_start_t:
                continue

            item_p = min(1.0, (t - item_start_t) / 0.35)
            item_e = ease_out_cubic(item_p)
            alpha = item_e
            slide_x = (1.0 - item_e) * 20.0

            row_y = bullets_start_y + i * row_height

            # Bullet dot: circle, color #6c63ff
            dot_center_x = margin_x + 6 + slide_x
            dot_center_y = row_y + 22
            draw.ellipse(
                [
                    dot_center_x - dot_radius,
                    dot_center_y - dot_radius,
                    dot_center_x + dot_radius,
                    dot_center_y + dot_radius,
                ],
                fill=hex_to_rgba("#6c63ff", alpha),
            )

            # Bullet text
            text_x = margin_x + 28 + slide_x
            draw.text(
                (text_x, row_y),
                item_text,
                fill=hex_to_rgba("#e0e0ff", alpha),
                font=font_bullet,
            )

        frames.append(canvas.convert("RGB"))

    return frames
