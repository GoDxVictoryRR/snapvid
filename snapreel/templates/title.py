"""Title card scene template renderer."""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    HEIGHT,
    WIDTH,
    create_canvas,
    draw_gradient_bar,
    ease_out_cubic,
    hex_to_rgba,
    load_font,
)


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS) -> list[Image.Image]:
    """Render title card frames with slide-up and fade-in animation.

    Args:
        data: Template data containing 'heading' and optional 'subheading'.
        duration: Duration of the scene in seconds.
        fps: Frames per second (default 30).

    Returns:
        List of RGB PIL Images.
    """
    total_frames = max(1, int(math.ceil(duration * fps)))
    heading_text = str(data.get("heading", ""))
    subheading_text = str(data.get("subheading") or "")

    font_heading = load_font(bold=True, size=56)
    font_subheading = load_font(bold=False, size=32)

    frames: list[Image.Image] = []

    # Calculate static dimensions
    temp_img = Image.new("RGBA", (WIDTH, HEIGHT))
    temp_draw = ImageDraw.Draw(temp_img)

    h_bbox = temp_draw.textbbox((0, 0), heading_text, font=font_heading)
    h_w = h_bbox[2] - h_bbox[0]
    h_h = h_bbox[3] - h_bbox[1]
    base_h_x = (WIDTH - h_w) // 2
    base_h_y = int(0.45 * HEIGHT) - (h_h // 2)

    line_w = 200
    line_h = 4
    line_x = (WIDTH - line_w) // 2
    line_y = base_h_y + h_h + 40

    if subheading_text:
        sub_bbox = temp_draw.textbbox((0, 0), subheading_text, font=font_subheading)
        sub_w = sub_bbox[2] - sub_bbox[0]
        base_sub_x = (WIDTH - sub_w) // 2
        base_sub_y = base_h_y + h_h + 80
    else:
        base_sub_x = 0
        base_sub_y = 0

    for f in range(total_frames):
        t = f / fps
        # Animate heading: slide up from +40px, opacity 0->1 over 0.5s
        p = min(1.0, t / 0.5) if duration > 0 else 1.0
        e = ease_out_cubic(p)
        alpha = e
        offset_y = (1.0 - e) * 40.0

        canvas = create_canvas()
        draw = ImageDraw.Draw(canvas)

        # Draw heading
        current_h_y = base_h_y + offset_y
        draw.text(
            (base_h_x, current_h_y),
            heading_text,
            fill=hex_to_rgba("#ffffff", alpha),
            font=font_heading,
        )

        # Draw accent gradient line (fade-in alongside heading)
        draw_gradient_bar(
            draw=draw,
            x=line_x,
            y=int(line_y + offset_y),
            w=line_w,
            h=line_h,
            start_hex="#6c63ff",
            end_hex="#48cae4",
            alpha=alpha,
            radius=2,
        )

        # Draw subheading (fade-in after 0.2s)
        if subheading_text:
            sub_p = max(0.0, min(1.0, (t - 0.2) / 0.4))
            sub_e = ease_out_cubic(sub_p)
            draw.text(
                (base_sub_x, base_sub_y + offset_y * 0.5),
                subheading_text,
                fill=hex_to_rgba("#e0e0ff", sub_e),
                font=font_subheading,
            )

        frames.append(canvas.convert("RGB"))

    return frames
