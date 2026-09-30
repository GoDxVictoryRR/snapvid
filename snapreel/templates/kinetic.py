"""Kinetic typography scene template renderer V2 with 5 animation styles."""

from __future__ import annotations

import math
from typing import Any
from PIL import Image, ImageDraw

from snapreel.templates.common import (
    DEFAULT_FPS,
    PALETTE,
    SIZES,
    apply_grain,
    draw_spaced_text,
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

KINETIC_COLORS = [
    PALETTE["text_hi"],
    PALETTE["accent1"],
    PALETTE["accent2"],
    PALETTE["accent3"],
    PALETTE["danger"],
]


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS, global_frame_offset: int = 0) -> list[Image.Image]:
    """Render kinetic typography supporting pop_in, slide_up, typewriter, word_highlight, scale_fade."""
    total_frames = max(1, math.ceil(duration * fps))
    raw_lines = data.get("lines", [])
    lines = [str(line) for line in raw_lines[:5]]
    style = str(data.get("style") or "pop_in").lower()
    align = str(data.get("align") or "center").lower()

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    margin_x = 60 if ratio != "9:16" else 36
    max_w = w - (margin_x * 2)

    # Dynamic auto-fitting font size so lines fit within max_w
    font_size = 42 if ratio != "9:16" else 30
    dummy = Image.new("RGBA", (1, 1))
    ddraw = ImageDraw.Draw(dummy)

    while font_size > 22:
        test_font = load_font(bold=True, size=font_size)
        if all((ddraw.textbbox((0, 0), l, font=test_font)[2] - ddraw.textbbox((0, 0), l, font=test_font)[0]) <= max_w for l in lines):
            break
        font_size -= 2

    font_line = load_font(bold=True, size=font_size)

    # Wrap any line that still exceeds max_w
    final_lines: list[str] = []
    line_color_indices: list[int] = []
    for orig_i, line in enumerate(lines):
        tb = ddraw.textbbox((0, 0), line, font=font_line)
        lw = tb[2] - tb[0]
        if lw > max_w:
            wrapped = wrap_text(line, font_line, max_w)
            final_lines.extend(wrapped)
            line_color_indices.extend([orig_i] * len(wrapped))
        else:
            final_lines.append(line)
            line_color_indices.append(orig_i)

    lines = final_lines[:6]
    line_color_indices = line_color_indices[:6]

    line_spacing = int(font_size * 1.35)
    total_block_h = len(lines) * line_spacing
    # If vertical block exceeds safe vertical space, shrink spacing
    if total_block_h > h - 160:
        line_spacing = max(int(font_size * 1.1), (h - 160) // max(1, len(lines)))
        total_block_h = len(lines) * line_spacing

    start_y = max(40, (h - total_block_h) // 2)

    # Measure lines
    line_metrics = []
    for line in lines:
        tb = ddraw.textbbox((0, 0), line, font=font_line)
        lw = tb[2] - tb[0]
        lh = tb[3] - tb[1]
        line_metrics.append((lw, lh))

    frames: list[Image.Image] = []

    # If word_highlight style, calculate word metadata
    all_words = []
    for i, line in enumerate(lines):
        words = line.split()
        for w_idx, wd in enumerate(words):
            all_words.append((i, w_idx, wd))
    total_words = max(1, len(all_words))
    word_interval = duration / total_words if total_words > 0 else 1.0

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)
        draw = ImageDraw.Draw(canvas)

        for i, line in enumerate(lines):
            lw, lh = line_metrics[i]
            raw_x = (w - lw) // 2 if align == "center" else margin_x
            target_x = max(margin_x, min(w - margin_x - lw, raw_x))
            final_y = start_y + i * line_spacing
            orig_color_idx = line_color_indices[i] if i < len(line_color_indices) else i
            color = KINETIC_COLORS[orig_color_idx % len(KINETIC_COLORS)]

            # ── Style 1: slide_up ─────────────────────────────────────────────
            if style == "slide_up":
                appear_t = 0.3 * i
                p = max(0.0, min(1.0, (t - appear_t) / 0.35)) if t >= appear_t else 0.0
                if p <= 0:
                    continue
                e = ease_out_cubic(p)
                offset_y = int(60 * (1.0 - e))
                cur_y = final_y + offset_y
                draw_text_shadowed(draw, (target_x, cur_y), line, font_line, hex_to_rgba(color, e))

            # ── Style 2: typewriter ───────────────────────────────────────────
            elif style == "typewriter":
                appear_t = 0.4 * i
                rel_t = max(0.0, t - appear_t)
                chars_count = len(line)
                # Reveal over 1.2s per line
                reveal_ratio = min(1.0, rel_t / 1.2) if chars_count > 0 else 1.0
                n_chars = int(reveal_ratio * chars_count)
                if n_chars > 0 or t >= appear_t:
                    visible_str = line[:n_chars]
                    end_x = draw_spaced_text(draw, target_x, final_y, visible_str, font_line, hex_to_rgba(color, 1.0))
                    # Blinking cursor rect: 3px wide, blink every 0.5s
                    blink = int(t * 2) % 2 == 0
                    if blink and reveal_ratio < 1.0:
                        draw.rectangle([end_x + 4, final_y, end_x + 7, final_y + lh], fill=hex_to_rgba(PALETTE["accent2"], 0.9))

            # ── Style 3: word_highlight ───────────────────────────────────────
            elif style == "word_highlight":
                words = line.split()
                # Draw words with positioning
                curr_word_x = target_x
                space_w = font_line.getbbox(" ")[2] - font_line.getbbox(" ")[0]
                for w_idx, wd in enumerate(words):
                    global_w_idx = sum(len(lines[prev].split()) for prev in range(i)) + w_idx
                    w_start_t = global_w_idx * word_interval
                    is_active = (w_start_t <= t < w_start_t + word_interval)

                    tb = draw.textbbox((0, 0), wd, font=font_line)
                    ww = tb[2] - tb[0]

                    if is_active:
                        w_p = min(1.0, (t - w_start_t) / max(0.1, word_interval * 0.5))
                        scale_e = ease_out_back(w_p)
                        w_color = hex_to_rgba(PALETTE["accent3"], 1.0)
                        draw_text_shadowed(draw, (int(curr_word_x), int(final_y - 3 * scale_e)), wd, font_line, w_color)
                    else:
                        w_color = hex_to_rgba(PALETTE["text_mid"], 0.35)
                        draw.text((curr_word_x, final_y), wd, fill=w_color, font=font_line)

                    curr_word_x += ww + space_w

            # ── Style 4 & 5: scale_fade & pop_in ──────────────────────────────
            else:  # pop_in or scale_fade
                appear_t = 0.4 * i
                if t < appear_t:
                    continue
                p = min(1.0, (t - appear_t) / 0.35)
                if style == "scale_fade":
                    e = ease_out_elastic(p)
                    scale = 0.75 + 0.25 * min(1.15, max(0.0, e))
                else:
                    e = ease_out_cubic(p)
                    scale = 0.8 + 0.2 * e

                alpha = min(1.0, max(0.0, p * 1.5))
                # Text with centered scale
                surf_w = max(1, int(lw * scale))
                surf_h = max(1, int(lh * scale))

                surf = Image.new("RGBA", (lw + 20, lh + 20), (0, 0, 0, 0))
                sdraw = ImageDraw.Draw(surf)
                sdraw.text((10, 10), line, fill=hex_to_rgba(color, alpha), font=font_line)

                resized = surf.resize((surf_w, surf_h), Image.Resampling.BILINEAR)
                dest_x = target_x - (surf_w - lw) // 2
                dest_y = final_y - (surf_h - lh) // 2
                if surf_w <= w - 20:
                    dest_x = max(10, min(w - surf_w - 10, dest_x))
                canvas.paste(resized, (dest_x, dest_y), resized)

        canvas = apply_grain(canvas, strength=0.02, frame_idx=f)
        frames.append(canvas.convert("RGB"))

    return frames
