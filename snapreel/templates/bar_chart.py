"""Bar chart scene template renderer."""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    create_canvas,
    draw_gradient_bar,
    ease_out_cubic,
    hex_to_rgba,
    load_font,
)


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS) -> list[Image.Image]:
    """Render horizontal animated bar chart frames.

    Args:
        data: Template data containing 'heading', 'labels', 'values', and optional 'unit'.
        duration: Duration of the scene in seconds.
        fps: Frames per second (default 30).

    Returns:
        List of RGB PIL Images.
    """
    total_frames = max(1, int(math.ceil(duration * fps)))
    heading_text = str(data.get("heading", ""))
    labels = [str(l) for l in data.get("labels", [])]
    raw_values = data.get("values", [])
    values = [float(v) for v in raw_values]
    unit_text = str(data.get("unit") or "").strip()

    count = min(len(labels), len(values), 8)
    labels = labels[:count]
    values = values[:count]

    font_heading = load_font(bold=True, size=52)
    font_label = load_font(bold=False, size=26)
    font_val = load_font(bold=True, size=26)

    margin_x = 80
    heading_y = 70
    start_y = 170

    bar_h = 44 if count > 6 else 48
    bar_gap = 12 if count > 6 else 16

    bar_start_x = 340
    max_bar_w = 680

    max_val = max(values) if values and max(values) > 0 else 1.0

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = create_canvas()
        draw = ImageDraw.Draw(canvas)

        # Draw heading
        h_alpha = min(1.0, t / 0.3)
        draw.text(
            (margin_x, heading_y),
            heading_text,
            fill=hex_to_rgba("#ffffff", h_alpha),
            font=font_heading,
        )

        for i in range(count):
            lbl = labels[i]
            val = values[i]
            y = start_y + i * (bar_h + bar_gap)

            # Draw label (left of bar, right aligned to bar_start_x - 20)
            lbl_bbox = draw.textbbox((0, 0), lbl, font=font_label)
            lbl_w = lbl_bbox[2] - lbl_bbox[0]
            lbl_h = lbl_bbox[3] - lbl_bbox[1]
            lbl_x = max(margin_x, bar_start_x - 24 - lbl_w)
            lbl_y = y + (bar_h - lbl_h) // 2 - 2

            draw.text(
                (lbl_x, lbl_y),
                lbl,
                fill=hex_to_rgba("#e0e0ff", 1.0),
                font=font_label,
            )

            # Animate bar grow over 0.6s
            stagger = 0.08 * i
            rel_t = max(0.0, t - stagger)
            p = min(1.0, rel_t / 0.6)
            e = ease_out_cubic(p)

            target_w = int((val / max_val) * max_bar_w) if max_val > 0 else 0
            curr_w = max(4, int(target_w * e)) if target_w > 0 else 0

            # Draw bar gradient
            if curr_w > 0:
                draw_gradient_bar(
                    draw=draw,
                    x=bar_start_x,
                    y=y,
                    w=curr_w,
                    h=bar_h,
                    start_hex="#6c63ff",
                    end_hex="#48cae4",
                    alpha=1.0,
                    radius=6,
                )

            # Draw value text right of bar
            val_str = f"{int(round(val))}" if val.is_integer() else f"{val:.1f}"
            if unit_text:
                val_str = f"{val_str} {unit_text}"

            val_bbox = draw.textbbox((0, 0), val_str, font=font_val)
            val_h = val_bbox[3] - val_bbox[1]
            val_x = bar_start_x + curr_w + 16
            val_y = y + (bar_h - val_h) // 2 - 2

            v_alpha = e
            draw.text(
                (val_x, val_y),
                val_str,
                fill=hex_to_rgba("#ffffff", v_alpha),
                font=font_val,
            )

        frames.append(canvas.convert("RGB"))

    return frames
