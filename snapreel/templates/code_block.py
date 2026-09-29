"""Code block scene template renderer with syntax highlighting and auto-scroll."""

from __future__ import annotations

import math
import re
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
            color = "#ffd166"
        elif kind == "COMMENT":
            color = "#7d8590"
        elif kind == "KEYWORD" and text.lower() in KEYWORDS:
            color = "#ef476f"
        else:
            color = "#e0e0ff"

        tokens.append((text, color))
        last_idx = match.end()

    if last_idx < len(line):
        tokens.append((line[last_idx:], "#e0e0ff"))

    return tokens


def render_frames(data: dict[str, Any], duration: float, fps: int = DEFAULT_FPS) -> list[Image.Image]:
    """Render code panel frames with syntax highlighting and scroll support.

    Args:
        data: Template data containing optional 'heading', 'language', and 'code'.
        duration: Duration of the scene in seconds.
        fps: Frames per second (default 30).

    Returns:
        List of RGB PIL Images.
    """
    total_frames = max(1, int(math.ceil(duration * fps)))
    heading_text = str(data.get("heading") or "").strip()
    language_text = str(data.get("language") or "").upper()
    code_text = str(data.get("code") or "")
    lines = code_text.splitlines() or [""]

    font_heading = load_font(bold=True, size=40)
    font_code = load_font(size=26, monospace=True)
    font_lang = load_font(bold=True, size=20)

    margin_x = 80
    panel_x = margin_x
    panel_w = WIDTH - (margin_x * 2)

    if heading_text:
        heading_y = 45
        panel_y = 110
        panel_h = HEIGHT - panel_y - 60
    else:
        heading_y = 0
        panel_y = 80
        panel_h = HEIGHT - (panel_y * 2)

    line_h = 36
    inner_pad_x = 36
    inner_pad_y = 52
    visible_code_h = panel_h - inner_pad_y - 20
    total_code_h = len(lines) * line_h
    max_scroll = max(0, total_code_h - visible_code_h + 20)

    # Pre-render complete code surface
    code_surface = Image.new("RGBA", (panel_w - inner_pad_x * 2, max(visible_code_h, total_code_h + 40)), (0, 0, 0, 0))
    code_draw = ImageDraw.Draw(code_surface)

    for i, line_str in enumerate(lines):
        y_pos = i * line_h
        tokens = highlight_tokens(line_str)
        curr_x = 0
        for token_text, token_color in tokens:
            code_draw.text(
                (curr_x, y_pos),
                token_text,
                fill=hex_to_rgba(token_color, 1.0),
                font=font_code,
            )
            tb = code_draw.textbbox((curr_x, y_pos), token_text, font=font_code)
            curr_x += (tb[2] - tb[0])

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = create_canvas()
        draw = ImageDraw.Draw(canvas)

        # Draw optional heading
        if heading_text:
            h_alpha = min(1.0, t / 0.3)
            draw.text(
                (margin_x, heading_y),
                heading_text,
                fill=hex_to_rgba("#ffffff", h_alpha),
                font=font_heading,
            )

        # Draw dark panel background and border
        panel_box = [panel_x, panel_y, panel_x + panel_w, panel_y + panel_h]
        draw.rounded_rectangle(
            panel_box,
            radius=14,
            fill=hex_to_rgba("#141424", 0.95),
            outline=hex_to_rgba("#6c63ff", 1.0),
            width=2,
        )

        # Draw window control dots (red, yellow, green)
        dot_y = panel_y + 22
        dot_r = 5
        dot_colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
        for idx, col in enumerate(dot_colors):
            dot_x = panel_x + 24 + idx * 18
            draw.ellipse(
                [dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
                fill=hex_to_rgba(col, 1.0),
            )

        # Draw language badge if present
        if language_text:
            lang_bbox = draw.textbbox((0, 0), language_text, font=font_lang)
            lang_w = lang_bbox[2] - lang_bbox[0]
            draw.text(
                (panel_x + panel_w - lang_w - 24, panel_y + 12),
                language_text,
                fill=hex_to_rgba("#7d8590", 1.0),
                font=font_lang,
            )

        # Calculate vertical scroll if code > 12 lines
        scroll_y = 0
        if max_scroll > 0 and len(lines) > 12:
            scroll_p = min(1.0, max(0.0, (t - 0.5) / max(0.1, duration - 1.0)))
            scroll_y = int(ease_out_cubic(scroll_p) * max_scroll)

        # Crop visible window of pre-rendered code
        crop_box = (
            0,
            scroll_y,
            panel_w - inner_pad_x * 2,
            scroll_y + visible_code_h,
        )
        visible_strip = code_surface.crop(crop_box)

        # Composite inside panel
        dest_x = panel_x + inner_pad_x
        dest_y = panel_y + inner_pad_y
        canvas.alpha_composite(visible_strip, dest=(dest_x, dest_y))

        frames.append(canvas.convert("RGB"))

    return frames
