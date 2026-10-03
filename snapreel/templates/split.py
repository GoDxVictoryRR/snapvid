"""Split layout scene template renderer (text left/top, visual right/bottom) with boundary safety."""

from __future__ import annotations

import math
from typing import Any, Callable, Optional
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    PALETTE,
    SIZES,
    apply_grain,
    draw_glass_card,
    draw_gradient_bar,
    draw_text_shadowed,
    ease_out_back,
    ease_out_cubic,
    ease_out_elastic,
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
    """Render split layout: explanation on left (or top in 9:16), data visual on right (or bottom in 9:16)."""
    total_frames = max(1, math.ceil(duration * fps))
    heading_text = str(data.get("heading") or "").strip()
    body_text = str(data.get("body") or "").strip()
    visual = str(data.get("visual") or "none").lower()
    visual_data = data.get("visual_data") or {}

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()
    is_vertical = ratio in ("9:16", "1:1")

    h2_size = 32 if is_vertical else (34 if ratio == "4:3" else 38)
    body_size = 22 if is_vertical else (24 if ratio == "4:3" else 28)
    caption_size = 18 if is_vertical else 22

    font_heading = load_font(bold=True, size=h2_size)
    font_body = load_font(bold=False, size=body_size)
    font_caption = load_font(bold=False, size=caption_size)
    font_num = load_font(bold=True, size=52 if is_vertical else 64)

    if is_vertical:
        card_w = w - 72
        half_h = int((h - 140) * 0.46)
        left_x = 36
        left_y = 50
        left_w = card_w
        left_h = half_h

        right_x = 36
        right_y = left_y + left_h + 30
        right_w = card_w
        right_h = half_h
    else:
        split_x = int(w * 0.5)
        margin = 40 if ratio == "4:3" else 50
        left_x = margin
        left_y = 60
        left_w = split_x - margin - 20
        left_h = h - 120

        right_x = split_x + 20
        right_y = 60
        right_w = w - split_x - margin - 20
        right_h = h - 120

    # Determine left and right text contents
    left_raw = str(data.get("left") or "").strip()
    right_raw = str(data.get("right") or "").strip()
    if left_raw and right_raw:
        left_content = left_raw
        right_content = right_raw
    else:
        left_content = body_text or left_raw
        right_content = right_raw or str(visual_data.get("text") or visual_data.get("body") or "").strip()

    # Wrap heading and body text inside left card
    max_text_w = left_w - 56
    heading_lines = wrap_text(heading_text, font_heading, max_text_w) if heading_text else []
    h_line_h = int(h2_size * 1.25)
    total_h_h = len(heading_lines) * h_line_h

    left_lines = wrap_text(left_content, font_body, max_text_w) if left_content else []
    b_line_h = int(body_size * 1.4)
    total_b_h = len(left_lines) * b_line_h

    # Vertical centering inside left card
    needed_left_h = total_h_h + (18 if heading_lines and left_lines else 0) + total_b_h
    left_top_pad = max(26, (left_h - needed_left_h) // 2) if left_h > needed_left_h + 40 else 26
    hy = left_y + left_top_pad
    by_start = hy + total_h_h + (18 if heading_lines else 0)

    # Wrap right text if needed
    max_right_w = right_w - 56
    right_lines = wrap_text(right_content, font_body, max_right_w) if right_content else []
    total_r_h = len(right_lines) * b_line_h
    right_top_pad = max(26, (right_h - total_r_h) // 2) if right_h > total_r_h + 40 else 26

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)

        # 1. Left (or Top) glass card
        draw_glass_card(canvas, left_x, left_y, left_w, left_h, radius=18)
        draw = ImageDraw.Draw(canvas)

        p = min(1.0, t / 0.4) if duration > 0 else 1.0
        e = ease_out_cubic(p)

        hx = left_x + 28

        # Draw wrapped heading lines
        h_col = hex_to_rgba(PALETTE["text_hi"], e)
        s_col = (0, 0, 0, int(120 * e))
        for i, hl in enumerate(heading_lines):
            draw_text_shadowed(draw, (hx, hy + i * h_line_h), hl, font_heading, h_col, s_col)

        # Draw wrapped body lines
        b_col = hex_to_rgba(PALETTE["text_mid"], e)
        for i, bl in enumerate(left_lines):
            cur_by = by_start + i * b_line_h
            if cur_by + b_line_h <= left_y + left_h - 16:
                draw.text((hx, cur_by), bl, fill=b_col, font=font_body)

        # 2. Divider line
        div_p = min(1.0, t / 0.5) if duration > 0 else 1.0
        if is_vertical:
            div_w = int((w - 100) * ease_out_cubic(div_p))
            div_x = (w - div_w) // 2
            div_y = left_y + left_h + 14
            draw_gradient_bar(
                draw=draw,
                x=div_x,
                y=div_y,
                w=div_w,
                h=2,
                start_hex=PALETTE["accent1"],
                end_hex=PALETTE["accent2"],
                alpha=0.6,
            )
        else:
            div_h = int((h - 140) * ease_out_cubic(div_p))
            div_y = 60 + (h - 120 - div_h) // 2
            draw_gradient_bar(
                draw=draw,
                x=int(w * 0.5) - 1,
                y=div_y,
                w=2,
                h=div_h,
                start_hex=PALETTE["accent1"],
                end_hex=PALETTE["accent2"],
                alpha=0.6,
            )

        # 3. Right (or Bottom) visual card
        draw_glass_card(canvas, right_x, right_y, right_w, right_h, radius=18)
        r_draw = ImageDraw.Draw(canvas)

        if visual == "counter":
            from_v = float(visual_data.get("from", 0))
            to_v = float(visual_data.get("to", 100))
            c_p = min(1.0, t / max(0.1, duration * 0.75))
            c_e = min(1.05, max(0.0, ease_out_elastic(c_p)))
            c_val = from_v + (to_v - from_v) * c_e
            val_str = f"{round(c_val):,}" if from_v.is_integer() and to_v.is_integer() else f"{c_val:.1f}"
            unit = str(visual_data.get("unit") or "").strip()
            label = str(visual_data.get("label") or "").strip()

            disp_str = f"{val_str} {unit}".strip()

            # Dynamic font scale if disp_str exceeds right card width
            curr_font_num = font_num
            tb = r_draw.textbbox((0, 0), disp_str, font=curr_font_num)
            str_w = tb[2] - tb[0]
            if str_w > right_w - 60:
                sc_size = max(24, int((right_w - 60) * 0.85))
                curr_font_num = load_font(bold=True, size=sc_size)

            cy = right_y + right_h // 2 - 10
            if label:
                r_draw.text((right_x + 28, cy - 40), label, fill=hex_to_rgba(PALETTE["text_low"], 1.0), font=font_caption)
            draw_text_shadowed(r_draw, (right_x + 28, cy), disp_str, curr_font_num, hex_to_rgba(PALETTE["accent1"], 1.0))

        elif visual == "bar":
            labels = visual_data.get("labels", ["A", "B", "C"])[:4]
            vals = [float(v) for v in visual_data.get("values", [10, 20, 30])[:len(labels)]]
            max_v = max(vals) if vals and max(vals) > 0 else 1.0
            
            # Center bars vertically inside right card
            n_bars = max(1, len(labels))
            total_bars_h = n_bars * 52
            by = right_y + max(24, (right_h - total_bars_h) // 2)
            max_lbl_w = 90
            bw_max = max(60, right_w - max_lbl_w - 80)

            for i, (lbl, val) in enumerate(zip(labels, vals)):
                iy = by + i * 52
                lbl_text = str(lbl)
                tb = r_draw.textbbox((0, 0), lbl_text, font=font_caption)
                if (tb[2] - tb[0]) > max_lbl_w:
                    lbl_text = lbl_text[:8] + ".."

                r_draw.text((right_x + 24, iy + 4), lbl_text, fill=hex_to_rgba(PALETTE["text_mid"], 1.0), font=font_caption)
                b_start = 0.2 + 0.15 * i
                b_p = min(1.0, max(0.0, (t - b_start) / 0.55)) if t >= b_start else 0.0
                b_w = max(4, int((val / max_v) * bw_max * ease_out_back(b_p)))
                draw_gradient_bar(
                    draw=r_draw,
                    x=right_x + max_lbl_w + 24,
                    y=iy,
                    w=b_w,
                    h=28,
                    start_hex=PALETTE["accent1"],
                    end_hex=PALETTE["accent2"],
                    alpha=1.0,
                    radius=4,
                )

        elif visual_data.get("value") or visual_data.get("metric"):
            # Metric / Stat visual
            metric_val = str(visual_data.get("value") or visual_data.get("metric") or "").strip()
            metric_lbl = str(visual_data.get("label") or visual_data.get("subtext") or "").strip()
            cy = right_y + right_h // 2 - 20
            if metric_lbl:
                r_draw.text((right_x + 32, cy - 36), metric_lbl, fill=hex_to_rgba(PALETTE["text_low"], e), font=font_caption)
            draw_text_shadowed(r_draw, (right_x + 32, cy), metric_val, font_num, hex_to_rgba(PALETTE["accent1"], e))

        elif right_lines:
            # Multi-line text in right card
            rx = right_x + 28
            r_col = hex_to_rgba(PALETTE["text_hi"], e)
            for i, rl in enumerate(right_lines):
                cur_ry = right_y + right_top_pad + i * b_line_h
                if cur_ry + b_line_h <= right_y + right_h - 16:
                    draw_text_shadowed(r_draw, (rx, cur_ry), rl, font_body, r_col)

        else:
            # Clean takeaway highlight placeholder
            accent_bar_y = right_y + right_h // 2 - 15
            draw_gradient_bar(
                draw=r_draw,
                x=right_x + 32,
                y=accent_bar_y,
                w=min(120, right_w - 64),
                h=4,
                start_hex=PALETTE["accent1"],
                end_hex=PALETTE["accent2"],
                alpha=0.8,
            )

        canvas = apply_grain(canvas, strength=0.015, frame_idx=f)
        out_f = canvas.convert("RGB")
        if on_frame is not None:
            on_frame(out_f, f)
        else:
            frames.append(out_f)

    return frames
