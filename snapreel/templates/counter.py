"""Counter scene template renderer V2."""

from __future__ import annotations

import math
from typing import Any, Callable, Optional
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    PALETTE,
    SIZES,
    apply_grain,
    draw_text_shadowed,
    ease_out_elastic,
    get_canvas_ratio,
    get_canvas_size,
    hex_to_rgba,
    load_font,
    make_animated_bg,
)


def render_frames(
    data: dict[str, Any],
    duration: float,
    fps: int = DEFAULT_FPS,
    global_frame_offset: int = 0,
    on_frame: Optional[Callable[[Image.Image, int], None]] = None,
) -> list[Image.Image]:
    """Render animated count-up frames with radial progress ring and boundary safety."""
    total_frames = max(1, math.ceil(duration * fps))
    label_text = str(data.get("label", "")).strip()

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

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    num_size = 64 if ratio == "9:16" else max(SIZES["display"], 88)
    label_size = 20 if ratio == "9:16" else SIZES["body"]
    unit_size = 24 if ratio == "9:16" else SIZES["h3"]

    font_number = load_font(bold=True, size=num_size)
    font_label = load_font(bold=False, size=label_size)
    font_unit = load_font(bold=True, size=unit_size)

    frames: list[Image.Image] = []
    anim_duration = max(0.1, 0.75 * duration)

    ring_r = min(180, int(min(w, h) * 0.28))
    center_x = w // 2
    center_y = h // 2 + 10

    for f in range(total_frames):
        t = f / fps
        p = min(1.0, t / anim_duration) if anim_duration > 0 else 1.0

        if p >= 1.0:
            e = 1.0
        elif p <= 0.0:
            e = 0.0
        else:
            e = min(1.05, max(0.0, ease_out_elastic(p)))

        curr_val = from_num + (to_num - from_num) * e
        if is_int:
            num_str = f"{round(curr_val):,}"
        else:
            num_str = f"{curr_val:.1f}"

        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)
        draw = ImageDraw.Draw(canvas)

        # 1. Radial progress ring behind number
        # sweeps from -90 deg (top) to -90 + 360 * p deg
        ring_box = [center_x - ring_r, center_y - ring_r, center_x + ring_r, center_y + ring_r]
        # background track
        draw.arc(ring_box, start=0, end=360, fill=hex_to_rgba(PALETTE["bg_card"], 0.5), width=4)
        sweep_end = -90 + int(360.0 * p)
        if sweep_end > -90:
            draw.arc(ring_box, start=-90, end=sweep_end, fill=hex_to_rgba(PALETTE["accent2"], 0.8), width=4)

        # 2. Measure number & unit
        num_bbox = draw.textbbox((0, 0), num_str, font=font_number)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]

        unit_w, unit_h = 0.0, 0.0
        if unit_text:
            unit_bbox = draw.textbbox((0, 0), unit_text, font=font_unit)
            unit_w = unit_bbox[2] - unit_bbox[0]
            unit_h = unit_bbox[3] - unit_bbox[1]

        total_row_w = num_w + (unit_w + 14 if unit_text else 0)
        num_x = max(16, min(w - 16 - total_row_w, int(center_x - (total_row_w // 2))))
        num_y = int(center_y - (num_h // 2))

        # Draw number
        draw_text_shadowed(
            draw,
            (num_x, num_y),
            num_str,
            font_number,
            hex_to_rgba(PALETTE["accent1"], 1.0),
            (0, 0, 0, 140),
        )

        # Draw unit inline right, aligned top
        if unit_text:
            unit_x = int(num_x + num_w + 14)
            unit_y = num_y + 8
            draw_text_shadowed(
                draw,
                (unit_x, unit_y),
                unit_text,
                font_unit,
                hex_to_rgba(PALETTE["text_mid"], 0.9),
                (0, 0, 0, 120),
            )

        # 3. Label: 60px above number
        if label_text:
            lbl_bbox = draw.textbbox((0, 0), label_text, font=font_label)
            lbl_w = lbl_bbox[2] - lbl_bbox[0]
            lbl_x = max(16, min(w - 16 - lbl_w, int(center_x - (lbl_w // 2))))
            lbl_y = num_y - 60
            draw_text_shadowed(
                draw,
                (lbl_x, lbl_y),
                label_text,
                font_label,
                hex_to_rgba(PALETTE["text_mid"], 1.0),
                (0, 0, 0, 120),
            )

        canvas = apply_grain(canvas, strength=0.02, frame_idx=f)
        out_f = canvas.convert("RGB")
        if on_frame is not None:
            on_frame(out_f, f)
        else:
            frames.append(out_f)

    return frames
