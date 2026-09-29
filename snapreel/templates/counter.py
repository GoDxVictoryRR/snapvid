"""Counter scene template renderer."""

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


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS) -> list[Image.Image]:
    """Render animated count-up frames with label and unit.

    Args:
        data: Template data containing 'label', 'from', 'to', and optional 'unit'.
        duration: Duration of the scene in seconds.
        fps: Frames per second (default 30).

    Returns:
        List of RGB PIL Images.
    """
    total_frames = max(1, int(math.ceil(duration * fps)))
    label_text = str(data.get("label", ""))

    from_val = data.get("from")
    if from_val is None:
        from_val = data.get("from_value", data.get("from_", 0))
    to_val = data.get("to", 100)

    try:
        from_num = float(from_val)
        to_num = float(to_val)
    except (TypeError, ValueError):
        from_num, to_num = 0.0, 100.0

    is_int = float(from_num).is_integer() and float(to_num).is_integer()
    unit_text = str(data.get("unit") or "").strip()

    font_number = load_font(bold=True, size=120)
    font_label = load_font(bold=False, size=36)
    font_unit = load_font(bold=True, size=40)

    frames: list[Image.Image] = []
    anim_duration = max(0.1, 0.8 * duration)

    for f in range(total_frames):
        t = f / fps
        p = min(1.0, t / anim_duration) if anim_duration > 0 else 1.0
        e = ease_out_cubic(p)
        curr_val = from_num + (to_num - from_num) * e

        if is_int:
            num_str = f"{int(round(curr_val)):,}"
        else:
            num_str = f"{curr_val:.1f}"

        canvas = create_canvas()
        draw = ImageDraw.Draw(canvas)

        # Measure dimensions
        num_bbox = draw.textbbox((0, 0), num_str, font=font_number)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]

        unit_w, unit_h = 0, 0
        if unit_text:
            unit_bbox = draw.textbbox((0, 0), unit_text, font=font_unit)
            unit_w = unit_bbox[2] - unit_bbox[0]
            unit_h = unit_bbox[3] - unit_bbox[1]

        total_row_w = num_w + (unit_w + 16 if unit_text else 0)

        # Center vertically and horizontally
        num_x = (WIDTH - total_row_w) // 2
        num_y = (HEIGHT - num_h) // 2 + 10

        # Draw number
        draw.text(
            (num_x, num_y),
            num_str,
            fill=hex_to_rgba("#6c63ff", 1.0),
            font=font_number,
        )

        # Draw unit to the right of number
        if unit_text:
            unit_x = num_x + num_w + 16
            unit_y = num_y + (num_h - unit_h) - 10
            draw.text(
                (unit_x, unit_y),
                unit_text,
                fill=hex_to_rgba("#48cae4", 1.0),
                font=font_unit,
            )

        # Draw label above number
        if label_text:
            label_bbox = draw.textbbox((0, 0), label_text, font=font_label)
            label_w = label_bbox[2] - label_bbox[0]
            label_x = (WIDTH - label_w) // 2
            label_y = num_y - 70

            # Fade label in slightly
            lbl_alpha = min(1.0, t / 0.3)
            draw.text(
                (label_x, label_y),
                label_text,
                fill=hex_to_rgba("#ffffff", lbl_alpha),
                font=font_label,
            )

        frames.append(canvas.convert("RGB"))

    return frames
