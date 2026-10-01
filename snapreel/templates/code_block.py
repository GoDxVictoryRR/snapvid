"""Code block scene template renderer V2 with line numbers, glass panel, syntax highlighting."""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Optional
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

KEYWORDS = {
    "def", "class", "import", "from", "return", "if", "elif", "else",
    "for", "while", "in", "try", "except", "finally", "with", "as",
    "async", "await", "function", "const", "let", "var", "echo", "export",
    "npm", "python", "pip", "true", "false", "none", "null", "self",
}

TOKEN_REGEX = re.compile(
    r'(?P<STRING>\"[^\"]*\"|\'[^\']*\')|'
    r'(?P<COMMENT>#.*|//.*)|'
    r'(?P<KEYWORD>\b[a-zA-Z_][a-zA-Z0-9_]*\b)|'
    r'(?P<OTHER>[^\s\w]+|\s+|\w+)'
)


def highlight_tokens(line: str) -> list[tuple[str, str]]:
    """Tokenize line and return list of (text, hex_color) tuples."""
    tokens: list[tuple[str, str]] = []
    last_idx = 0
    for match in TOKEN_REGEX.finditer(line):
        text = match.group()
        kind = match.lastgroup
        if kind == "STRING":
            color = PALETTE["accent3"]
        elif kind == "COMMENT":
            color = PALETTE["text_low"]
        elif kind == "KEYWORD" and text.lower() in KEYWORDS:
            color = PALETTE["danger"]
        else:
            color = PALETTE["text_hi"]
        tokens.append((text, color))
        last_idx = match.end()

    if last_idx < len(line):
        tokens.append((line[last_idx:], PALETTE["text_hi"]))
    return tokens


def render_frames(
    data: dict[str, Any],
    duration: float,
    fps: int = DEFAULT_FPS,
    global_frame_offset: int = 0,
    on_frame: Optional[Callable[[Image.Image, int], None]] = None,
) -> list[Image.Image]:
    """Render code panel frames with glass styling, line numbers, and scrolling."""
    total_frames = max(1, math.ceil(duration * fps))
    heading_text = str(data.get("heading") or "").strip()
    language_text = str(data.get("language") or "").upper()
    code_text = str(data.get("code") or "")
    lines = code_text.splitlines() or [""]

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    h3_size = 26 if ratio == "9:16" else SIZES["h3"]
    code_size = 18 if ratio == "9:16" else SIZES["mono"]

    font_heading = load_font(bold=True, size=h3_size)
    font_code = load_font(size=code_size, monospace=True)
    font_lang = load_font(bold=True, size=16 if ratio == "9:16" else 18)
    font_line_num = load_font(size=max(12, code_size - 2), monospace=True)

    margin_x = 36 if ratio == "9:16" else 70
    panel_x = margin_x
    panel_w = w - (margin_x * 2)

    h_line_h = int(h3_size * 1.25)
    heading_lines = wrap_text(heading_text, font_heading, panel_w) if heading_text else []

    if heading_lines:
        heading_y = 25
        panel_y = heading_y + len(heading_lines) * h_line_h + 14
        panel_h = h - panel_y - (25 if ratio == "9:16" else 40)
    else:
        heading_y = 0
        panel_y = 50 if ratio == "9:16" else 65
        panel_h = h - (panel_y * 2)

    line_h = 28 if ratio == "9:16" else 34
    inner_pad_x = 18 if ratio == "9:16" else 24
    inner_pad_y = 44 if ratio == "9:16" else 48
    line_num_w = 32 if ratio == "9:16" else 40
    visible_code_h = max(20, panel_h - inner_pad_y - 16)
    total_code_h = len(lines) * line_h
    max_scroll = max(0, total_code_h - visible_code_h + 20)

    # Pre-render code surface with line numbers
    surf_w = max(10, panel_w - inner_pad_x * 2)
    surf_h = max(visible_code_h, total_code_h + 40)
    code_surface = Image.new("RGBA", (surf_w, surf_h), (0, 0, 0, 0))
    code_draw = ImageDraw.Draw(code_surface)

    for i, line_str in enumerate(lines):
        y_pos = i * line_h
        # Draw line number
        num_str = f"{i + 1:2d}"
        code_draw.text((0, y_pos), num_str, fill=hex_to_rgba(PALETTE["text_low"], 0.7), font=font_line_num)

        # Draw syntax highlighted tokens
        tokens = highlight_tokens(line_str)
        curr_x = line_num_w
        for token_text, token_color in tokens:
            code_draw.text((curr_x, y_pos), token_text, fill=hex_to_rgba(token_color, 1.0), font=font_code)
            tb = code_draw.textbbox((curr_x, y_pos), token_text, font=font_code)
            curr_x += (tb[2] - tb[0])

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)

        # Draw optional heading
        draw = ImageDraw.Draw(canvas)
        if heading_lines:
            h_alpha = min(1.0, t / 0.3)
            h_col = hex_to_rgba(PALETTE["text_hi"], h_alpha)
            s_col = (0, 0, 0, int(120 * h_alpha))
            for i, hl in enumerate(heading_lines):
                draw_text_shadowed(
                    draw,
                    (margin_x, heading_y + i * h_line_h),
                    hl,
                    font_heading,
                    h_col,
                    s_col,
                )

        # Glass card panel
        draw_glass_card(
            canvas,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            bg_hex=PALETTE["bg_deep"],
            bg_alpha=0.88,
            border_hex=PALETTE["accent1"],
            border_alpha=0.5,
            radius=16,
        )

        draw = ImageDraw.Draw(canvas)

        # Window controls dots
        dot_y = panel_y + 20
        dot_r = 5
        dot_colors = [PALETTE["danger"], PALETTE["accent3"], PALETTE["success"]]
        for idx, col in enumerate(dot_colors):
            dot_x = panel_x + 20 + idx * 16
            draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=hex_to_rgba(col, 1.0))

        # Language badge
        if language_text:
            lang_bbox = draw.textbbox((0, 0), language_text, font=font_lang)
            lang_w = lang_bbox[2] - lang_bbox[0]
            draw.text(
                (panel_x + panel_w - lang_w - 20, panel_y + 12),
                language_text,
                fill=hex_to_rgba(PALETTE["text_mid"], 0.8),
                font=font_lang,
            )

        # Auto-scroll if long
        scroll_y = 0
        if max_scroll > 0 and len(lines) > 10:
            scroll_p = min(1.0, max(0.0, (t - 0.5) / max(0.1, duration - 1.0)))
            scroll_y = int(ease_out_cubic(scroll_p) * max_scroll)

        crop_box = (0, scroll_y, panel_w - inner_pad_x * 2, scroll_y + visible_code_h)
        visible_strip = code_surface.crop(crop_box)

        canvas.alpha_composite(visible_strip, dest=(panel_x + inner_pad_x, panel_y + inner_pad_y))
        canvas = apply_grain(canvas, strength=0.015, frame_idx=f)
        out_f = canvas.convert("RGB")
        if on_frame is not None:
            on_frame(out_f, f)
        else:
            frames.append(out_f)

    return frames
