"""Bullet list scene template renderer V2 with auto-wrapping and bounds safety."""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    PALETTE,
    SIZES,
    apply_grain,
    draw_glass_card,
    draw_text_shadowed,
    ease_out_cubic,
    get_canvas_ratio,
    get_canvas_size,
    hex_to_rgba,
    load_font,
    make_animated_bg,
    wrap_text,
)


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS, global_frame_offset: int = 0) -> list[Image.Image]:
    """Render bullet list with frosted glass card container, multi-line wrapping, and staggered reveals."""
    total_frames = max(1, math.ceil(duration * fps))
    heading_text = str(data.get("heading", "")).strip()
    raw_items = data.get("items", [])
    items = [str(item).strip() for item in raw_items[:6]]

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    card_x = 36 if ratio == "9:16" else 70
    card_y = 50 if ratio == "9:16" else 70
    card_w = w - (card_x * 2)
    card_h = h - (card_y * 2)

    heading_x = card_x + 32
    heading_y = card_y + 30
    max_heading_w = card_w - 64

    h2_size = 32 if ratio == "9:16" else SIZES["h2"]
    body_size = 20 if ratio == "9:16" else (22 if ratio == "4:3" else SIZES["body"])

    font_heading = load_font(bold=True, size=h2_size)
    heading_lines = wrap_text(heading_text, font_heading, max_heading_w) if heading_text else []
    h_line_h = int(h2_size * 1.25)
    total_h_h = len(heading_lines) * h_line_h

    bullets_start_y = heading_y + total_h_h + (24 if heading_lines else 10)
    avail_h = card_h - (bullets_start_y - card_y) - 24

    dot_r = 5
    dot_cx = heading_x + 8
    text_x = dot_cx + 20
    max_bullet_w = (card_x + card_w - 32) - text_x

    # Font sizing & wrapping loop to ensure all bullets fit vertically inside the card
    while body_size >= 16:
        font_bullet = load_font(bold=False, size=body_size)
        bullet_line_h = int(body_size * 1.35)
        wrapped_items = [wrap_text(it, font_bullet, max_bullet_w) for it in items]
        total_lines = sum(max(1, len(wl)) for wl in wrapped_items)
        n_items = max(1, len(items))
        gap = max(8, min(24, (avail_h - total_lines * bullet_line_h) // max(1, n_items)))
        needed_h = total_lines * bullet_line_h + (n_items - 1) * gap
        if needed_h <= avail_h or body_size <= 16:
            break
        body_size -= 2

    # Compute vertical offsets for each bullet item
    item_offsets: list[int] = []
    item_heights: list[int] = []
    cur_y = bullets_start_y
    for wl in wrapped_items:
        item_offsets.append(cur_y)
        ih = max(1, len(wl)) * bullet_line_h
        item_heights.append(ih)
        cur_y += ih + gap

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)

        # 1. Glass card container
        draw_glass_card(
            canvas,
            card_x,
            card_y,
            card_w,
            card_h,
            bg_hex="#ffffff",
            bg_alpha=0.06,
            border_hex=PALETTE["accent1"],
            border_alpha=0.4,
            radius=18,
        )

        draw = ImageDraw.Draw(canvas)

        # 2. Heading inside card
        if heading_lines:
            h_p = min(1.0, t / 0.4) if duration > 0 else 1.0
            h_e = ease_out_cubic(h_p)
            h_col = hex_to_rgba(PALETTE["text_hi"], h_e)
            s_col = (0, 0, 0, int(120 * h_e))
            for i, hl in enumerate(heading_lines):
                draw_text_shadowed(
                    draw,
                    (heading_x, heading_y + i * h_line_h),
                    hl,
                    font_heading,
                    h_col,
                    s_col,
                )

        # 3. Bullet items staggered across scene duration
        n_items = max(1, len(items))
        reveal_window = min(max(1.0, duration * 0.65), 1.2 * n_items)
        step = reveal_window / n_items

        for i, (wl, item_y, ih) in enumerate(zip(wrapped_items, item_offsets, item_heights)):
            item_start = 0.25 + i * step
            if t < item_start:
                continue

            item_p = min(1.0, (t - item_start) / 0.35)
            item_e = ease_out_cubic(item_p)
            slide_y = (1.0 - item_e) * 20.0

            cur_item_y = int(item_y + slide_y)
            dot_cy = cur_item_y + int(bullet_line_h * 0.5)

            # Accent dot
            draw.ellipse(
                [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
                fill=hex_to_rgba(PALETTE["accent1"], item_e),
            )

            # Multi-line bullet text
            b_col = hex_to_rgba(PALETTE["text_mid"], item_e)
            b_shadow = (0, 0, 0, int(100 * item_e))
            for li, line in enumerate(wl):
                ly = cur_item_y + li * bullet_line_h
                draw_text_shadowed(
                    draw,
                    (text_x, ly),
                    line,
                    font_bullet,
                    b_col,
                    b_shadow,
                )

            # Subtle separator line except last item
            if i < len(items) - 1 and item_e > 0.5:
                sep_y = cur_item_y + ih + gap // 2
                draw.line(
                    [(heading_x, sep_y), (card_x + card_w - 32, sep_y)],
                    fill=hex_to_rgba(PALETTE["bg_card"], 0.6 * item_e),
                    width=1,
                )

        canvas = apply_grain(canvas, strength=0.02, frame_idx=f)
        frames.append(canvas.convert("RGB"))

    return frames
