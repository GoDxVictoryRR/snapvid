"""Kinetic typography scene template renderer."""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    HEIGHT,
    WIDTH,
    create_canvas,
    ease_out_cubic,
    hex_to_rgba,
    load_font,
)

KINETIC_COLORS = ["#ffffff", "#6c63ff", "#48cae4", "#ffd166", "#ef476f"]


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS) -> list[Image.Image]:
    """Render kinetic text with sequential appear, scale-up, and color styling.

    Args:
        data: Template data containing 'lines' list.
        duration: Duration of the scene in seconds.
        fps: Frames per second (default 30).

    Returns:
        List of RGB PIL Images.
    """
    total_frames = max(1, int(math.ceil(duration * fps)))
    raw_lines = data.get("lines", [])
    lines = [str(line) for line in raw_lines[:5]]

    font_line = load_font(bold=True, size=52)
    line_spacing = 80
    total_block_h = len(lines) * line_spacing
    start_y = (HEIGHT - total_block_h) // 2

    frames: list[Image.Image] = []

    # Pre-render text surfaces for clean scaling and alpha composition
    dummy = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy)

    rendered_lines = []
    for i, line_text in enumerate(lines):
        bbox = dummy_draw.textbbox((0, 0), line_text, font=font_line)
        tw = max(1, bbox[2] - bbox[0])
        th = max(1, bbox[3] - bbox[1])
        pad = 20
        surf = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(surf)
        color = KINETIC_COLORS[i % len(KINETIC_COLORS)]
        sdraw.text((pad - bbox[0], pad - bbox[1]), line_text, fill=color, font=font_line)
        rendered_lines.append((surf, tw + pad * 2, th + pad * 2))

    for f in range(total_frames):
        t = f / fps
        canvas = create_canvas()

        for i, (surf, sw, sh) in enumerate(rendered_lines):
            appear_t = 0.5 * i
            if t < appear_t:
                continue

            # Animate 0.8 -> 1.0 scale and 0 -> 1 opacity over 0.3s
            p = min(1.0, (t - appear_t) / 0.3)
            e = ease_out_cubic(p)
            scale = 0.8 + 0.2 * e
            alpha = e

            curr_w = max(1, int(sw * scale))
            curr_h = max(1, int(sh * scale))

            # Resize surface
            scaled_surf = surf.resize((curr_w, curr_h), Image.Resampling.BILINEAR)

            # Apply alpha
            if alpha < 0.99:
                r, g, b, a = scaled_surf.split()
                a = a.point(lambda p: int(p * alpha))
                scaled_surf.putalpha(a)

            target_center_x = WIDTH // 2
            target_center_y = start_y + i * line_spacing + (line_spacing // 2)

            dest_x = target_center_x - (curr_w // 2)
            dest_y = target_center_y - (curr_h // 2)

            canvas.alpha_composite(scaled_surf, dest=(dest_x, dest_y))

        frames.append(canvas.convert("RGB"))

    return frames
