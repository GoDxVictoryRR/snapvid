"""Title card scene template renderer V2."""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    PALETTE,
    SIZES,
    apply_grain,
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
    """Render title card frames with animated bg, text shadow, glow accent bar, and slide-up."""
    total_frames = max(1, math.ceil(duration * fps))
    heading_text = str(data.get("heading", ""))
    subheading_text = str(data.get("subheading") or "")

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    h1_size = 46 if ratio == "9:16" else SIZES["h1"]
    body_size = 24 if ratio == "9:16" else SIZES["body"]

    font_heading = load_font(bold=True, size=h1_size)
    font_subheading = load_font(bold=False, size=body_size)

    temp_img = Image.new("RGBA", (w, h))
    temp_draw = ImageDraw.Draw(temp_img)

    max_w = w - (120 if ratio != "9:16" else 70)

    # Wrap heading into lines if it exceeds safe width
    heading_lines = wrap_text(heading_text, font_heading, max_w) if heading_text else [""]
    h_line_h = int(h1_size * 1.25)
    total_h_h = len(heading_lines) * h_line_h

    # Wrap subheading into lines if present
    sub_lines = wrap_text(subheading_text, font_subheading, max_w) if subheading_text else []
    sub_line_h = int(body_size * 1.35)
    total_sub_h = len(sub_lines) * sub_line_h

    # Calculate total block height and vertical center
    bar_gap = 18
    total_block_h = total_h_h + bar_gap + 8 + (total_sub_h + 20 if sub_lines else 0)
    base_h_y = max(40, int(0.42 * h) - (total_block_h // 2))

    # Pre-measure heading line widths for centering
    h_widths = []
    for hl in heading_lines:
        bb = temp_draw.textbbox((0, 0), hl, font=font_heading)
        h_widths.append(bb[2] - bb[0])
    max_h_w = max(h_widths) if h_widths else 200

    bar_w = min(max_w, max(160, min(500, max_h_w + 30)))
    bar_x = (w - bar_w) // 2
    bar_y = base_h_y + total_h_h + bar_gap

    # Pre-measure sub lines
    sub_widths = []
    for sl in sub_lines:
        bb = temp_draw.textbbox((0, 0), sl, font=font_subheading)
        sub_widths.append(bb[2] - bb[0])
    base_sub_y = bar_y + 24

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        p = min(1.0, t / 0.5) if duration > 0 else 1.0
        e = ease_out_cubic(p)
        offset_y = (1.0 - e) * 40.0

        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)
        draw = ImageDraw.Draw(canvas)

        # 1. Heading lines with shadow
        cur_h_y = int(base_h_y + offset_y)
        h_color = hex_to_rgba(PALETTE["text_hi"], e)
        s_color = (0, 0, 0, int(140 * e))
        for i, (hl, hw) in enumerate(zip(heading_lines, h_widths)):
            hx = max(24, min(w - 24 - hw, (w - hw) // 2))
            draw_text_shadowed(draw, (hx, cur_h_y + i * h_line_h), hl, font_heading, h_color, s_color)

        # 2. Accent bar + glow (fade in after heading, around t >= 0.3s)
        bar_p = max(0.0, min(1.0, (t - 0.3) / 0.3)) if duration > 0.3 else e
        if bar_p > 0:
            cur_bar_y = int(bar_y + offset_y)
            # Subtle glow: draw 8px blur-sim bar in accent1 at 30% alpha
            draw_gradient_bar(
                draw=draw,
                x=bar_x - 10,
                y=cur_bar_y - 2,
                w=bar_w + 20,
                h=8,
                start_hex=PALETTE["accent1"],
                end_hex=PALETTE["accent1"],
                alpha=0.30 * bar_p,
                radius=4,
            )
            # Main 3px gradient bar
            draw_gradient_bar(
                draw=draw,
                x=bar_x,
                y=cur_bar_y,
                w=bar_w,
                h=3,
                start_hex=PALETTE["accent1"],
                end_hex=PALETTE["accent2"],
                alpha=bar_p,
                radius=2,
            )

        # 3. Subheading lines (fade in at t >= 0.7s or earlier for short scenes)
        if sub_lines:
            sub_start = min(0.7, max(0.2, duration * 0.3))
            sub_p = max(0.0, min(1.0, (t - sub_start) / 0.4))
            if sub_p > 0:
                cur_sub_y = int(base_sub_y + offset_y)
                sub_color = hex_to_rgba(PALETTE["text_mid"], ease_out_cubic(sub_p))
                sub_shadow = (0, 0, 0, int(100 * sub_p))
                for i, (sl, sw) in enumerate(zip(sub_lines, sub_widths)):
                    sx = max(24, min(w - 24 - sw, (w - sw) // 2))
                    draw_text_shadowed(
                        draw,
                        (sx, cur_sub_y + i * sub_line_h),
                        sl,
                        font_subheading,
                        sub_color,
                        sub_shadow,
                    )

        canvas = apply_grain(canvas, strength=0.025, frame_idx=f)
        frames.append(canvas.convert("RGB"))

    return frames
