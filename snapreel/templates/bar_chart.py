"""Bar chart scene template renderer V2."""

from __future__ import annotations

import math
from typing import Any, Callable, Optional
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    PALETTE,
    SIZES,
    apply_grain,
    draw_gradient_bar,
    draw_text_shadowed,
    ease_out_back,
    get_canvas_ratio,
    get_canvas_size,
    hex_to_rgba,
    load_font,
    make_animated_bg,
    wrap_text,
)


def render_frames(
    data: dict[str, Any],
    duration: float,
    fps: int = DEFAULT_FPS,
    global_frame_offset: int = 0,
    on_frame: Optional[Callable[[Image.Image, int], None]] = None,
) -> list[Image.Image]:
    """Render horizontal animated bar chart frames per TEMPLATES_V2.md."""
    total_frames = max(1, math.ceil(duration * fps))
    heading_text = str(data.get("heading", ""))
    labels = [str(l) for l in data.get("labels", [])]
    raw_values = data.get("values", [])
    values = [float(v) for v in raw_values]
    unit_text = str(data.get("unit") or "").strip()

    count = min(len(labels), len(values), 8)
    labels = labels[:count]
    values = values[:count]
    max_val = max(values) if values and max(values) > 0 else 1.0

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    n = max(1, count)
    if n <= 4:
        h2_size = 36 if ratio == "9:16" else 48
        caption_size = 20 if ratio == "9:16" else 26
    else:
        h2_size = 32 if ratio == "9:16" else SIZES["h2"]
        caption_size = 18 if ratio == "9:16" else SIZES["caption"]

    font_heading = load_font(bold=True, size=h2_size)
    font_caption = load_font(bold=False, size=caption_size)
    font_val = load_font(bold=True, size=caption_size)

    heading_lines = wrap_text(heading_text, font_heading, w - 80) if heading_text else []
    h_line_h = int(h2_size * 1.25)
    total_h_h = len(heading_lines) * h_line_h

    left_margin = int(w * 0.28) if ratio == "9:16" else int(w * 0.26)
    max_bar_w = int(w * 0.44) if ratio == "9:16" else int(w * 0.52)

    avail_h = h - total_h_h - 120
    bar_h = min(52, max(24, (avail_h // n) - 16))
    bar_gap = max(12, min(32, (avail_h - n * bar_h) // max(1, n)))
    total_bars_h = n * bar_h + (n - 1) * bar_gap

    total_chart_h = total_h_h + (30 if heading_lines else 0) + total_bars_h
    if total_chart_h < h - 80:
        heading_y = max(35, (h - total_chart_h) // 2 - 10)
        start_y = heading_y + total_h_h + (30 if heading_lines else 0)
    else:
        heading_y = 35 if ratio == "9:16" else 45
        start_y = heading_y + total_h_h + (30 if heading_lines else 20)

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)
        draw = ImageDraw.Draw(canvas)

        # 1. Heading with shadow
        if heading_lines:
            h_alpha = min(1.0, t / 0.3) if duration > 0 else 1.0
            h_col = hex_to_rgba(PALETTE["text_hi"], h_alpha)
            s_col = (0, 0, 0, int(120 * h_alpha))
            for i, hl in enumerate(heading_lines):
                draw_text_shadowed(
                    draw,
                    (36 if ratio == "9:16" else 70, heading_y + i * h_line_h),
                    hl,
                    font_heading,
                    h_col,
                    s_col,
                )

        for i in range(count):
            lbl = labels[i]
            val = values[i]
            y = start_y + i * (bar_h + bar_gap)

            # Label: right-aligned before bar, truncated if too long
            lbl_bbox = draw.textbbox((0, 0), lbl, font=font_caption)
            lbl_w = lbl_bbox[2] - lbl_bbox[0]
            max_lbl_avail = left_margin - 30
            if lbl_w > max_lbl_avail:
                lbl = lbl[:10] + ".."
                lbl_bbox = draw.textbbox((0, 0), lbl, font=font_caption)
                lbl_w = lbl_bbox[2] - lbl_bbox[0]

            lbl_h = lbl_bbox[3] - lbl_bbox[1]
            lbl_x = max(15, left_margin - 14 - lbl_w)
            lbl_y = y + (bar_h - lbl_h) // 2

            draw.text(
                (lbl_x, lbl_y),
                lbl,
                fill=hex_to_rgba(PALETTE["text_mid"], 1.0),
                font=font_caption,
            )

            # Track background
            draw_gradient_bar(
                draw=draw,
                x=left_margin,
                y=y,
                w=max_bar_w,
                h=bar_h,
                start_hex=PALETTE["bg_card"],
                end_hex=PALETTE["bg_card"],
                alpha=0.45,
                radius=4,
            )

            # Animate bar grow with ease_out_back spaced across scene duration
            reveal_window = min(max(0.8, duration * 0.6), 0.9 * max(1, count))
            step = reveal_window / max(1, count)
            t_start = 0.25 + i * step
            rel_t = max(0.0, t - t_start)
            p = min(1.0, rel_t / 0.65) if rel_t > 0 else 0.0
            e = ease_out_back(p)

            target_w = int((val / max_val) * max_bar_w) if max_val > 0 else 0
            curr_w = max(0, min(max_bar_w, int(target_w * max(0.0, e))))

            if curr_w > 0:
                draw_gradient_bar(
                    draw=draw,
                    x=left_margin,
                    y=y,
                    w=curr_w,
                    h=bar_h,
                    start_hex=PALETTE["accent1"],
                    end_hex=PALETTE["accent2"],
                    alpha=1.0,
                    radius=4,
                )

            # Value label: appears right of bar when bar > 80% grown (p > 0.8)
            if p > 0.8:
                val_str = f"{int(val)}" if val.is_integer() else f"{val:.1f}"
                if unit_text:
                    val_str = f"{val_str} {unit_text}"

                val_bbox = draw.textbbox((0, 0), val_str, font=font_val)
                val_w = val_bbox[2] - val_bbox[0]
                val_h = val_bbox[3] - val_bbox[1]
                val_x = left_margin + curr_w + 10
                if val_x + val_w > w - 16:
                    val_x = max(left_margin + 6, w - val_w - 16)
                val_y = int(y + (bar_h - val_h) // 2)
                val_alpha = min(1.0, (p - 0.8) / 0.2)

                draw_text_shadowed(
                    draw,
                    (val_x, val_y),
                    val_str,
                    font_val,
                    hex_to_rgba(PALETTE["text_hi"], val_alpha),
                    (0, 0, 0, int(100 * val_alpha)),
                )

        canvas = apply_grain(canvas, strength=0.02, frame_idx=f)
        out_f = canvas.convert("RGB")
        if on_frame is not None:
            on_frame(out_f, f)
        else:
            frames.append(out_f)

    return frames
