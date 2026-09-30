"""Quote scene template renderer."""

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
    draw_gradient_bar,
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
    """Render quote card supporting centered and card styles with boundary protection."""
    total_frames = max(1, math.ceil(duration * fps))
    quote_text = f'"{str(data.get("text") or "").strip()}"'
    attribution = str(data.get("attribution") or "").strip()
    style = str(data.get("style") or "centered").lower()

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    q_size = 28 if ratio == "9:16" else (SIZES["h2"] - 4)
    font_quote = load_font(bold=False, size=q_size)
    font_attr = load_font(bold=False, size=18 if ratio == "9:16" else SIZES["caption"])
    font_mark = load_font(bold=True, size=int(SIZES["display"] * (1.1 if ratio == "9:16" else 1.5)))

    max_w = min(1000, w - (80 if ratio == "9:16" else 160))
    lines = wrap_text(quote_text, font_quote, max_w)
    line_h = int(q_size * 1.35)
    text_block_h = len(lines) * line_h

    center_x = w // 2
    center_y = int(h * 0.44)
    start_y = max(50, center_y - (text_block_h // 2))

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)

        # If card style, draw frosted glass card behind
        if style == "card":
            card_w = min(w - 60, 940)
            card_h = text_block_h + (160 if attribution else 120)
            card_x = (w - card_w) // 2
            card_y = start_y - 40
            draw_glass_card(canvas, card_x, card_y, card_w, card_h, radius=20)

        draw = ImageDraw.Draw(canvas)

        # Entrance: scale 0.9 -> 1.0, fade in over 0.6s
        p = min(1.0, t / 0.6) if duration > 0 else 1.0
        e = ease_out_cubic(p)

        # Large quotation mark "❝"
        mark_alpha = 0.15 * e
        draw.text((36 if ratio == "9:16" else 60, start_y - 60), "❝", fill=hex_to_rgba(PALETTE["accent1"], mark_alpha), font=font_mark)

        # Quote text lines
        for i, line in enumerate(lines):
            tb = draw.textbbox((0, 0), line, font=font_quote)
            lw = tb[2] - tb[0]
            lx = max(24, min(w - 24 - lw, int(center_x - (lw // 2))))
            ly = start_y + i * line_h
            draw_text_shadowed(
                draw,
                (lx, ly),
                line,
                font_quote,
                hex_to_rgba(PALETTE["text_hi"], e),
                (0, 0, 0, int(130 * e)),
            )

        # Attribution fade in at t >= 0.6s
        attr_y = start_y + text_block_h + 30
        if attribution:
            attr_start = min(0.6, duration * 0.4)
            attr_p = max(0.0, min(1.0, (t - attr_start) / 0.4))
            if attr_p > 0:
                attr_text = f"— {attribution}"
                tb = draw.textbbox((0, 0), attr_text, font=font_attr)
                aw = tb[2] - tb[0]
                ax = max(24, min(w - 24 - aw, int(center_x - (aw // 2))))
                draw.text((ax, attr_y), attr_text, fill=hex_to_rgba(PALETTE["text_mid"], attr_p), font=font_attr)

        # Bottom accent bar: 120px wide, 3px, centered
        bar_w = 120
        bar_x = center_x - (bar_w // 2)
        bar_y = attr_y + (40 if attribution else 20)
        draw_gradient_bar(
            draw=draw,
            x=bar_x,
            y=bar_y,
            w=bar_w,
            h=3,
            start_hex=PALETTE["accent1"],
            end_hex=PALETTE["accent2"],
            alpha=e,
            radius=2,
        )

        canvas = apply_grain(canvas, strength=0.02, frame_idx=f)
        frames.append(canvas.convert("RGB"))

    return frames
