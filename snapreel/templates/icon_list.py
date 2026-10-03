"""Icon list scene template renderer with vector geometry icons and boundary safety."""

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
    draw_text_shadowed,
    ease_out_cubic,
    get_canvas_ratio,
    get_canvas_size,
    hex_to_rgba,
    load_font,
    make_animated_bg,
    wrap_text,
)


def _star_points(cx: float, cy: float, r: float, points: int = 5) -> list[tuple[float, float]]:
    pts = []
    inner_r = r * 0.45
    for i in range(points * 2):
        angle = i * math.pi / points - math.pi / 2
        curr_r = r if i % 2 == 0 else inner_r
        pts.append((cx + curr_r * math.cos(angle), cy + curr_r * math.sin(angle)))
    return pts


def draw_icon(d: ImageDraw.ImageDraw, icon_name: str, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    """Draw vector icon using pure Pillow geometry."""
    name = icon_name.lower()
    if name == "circle":
        d.ellipse([x, y, x + 24, y + 24], fill=color)
    elif name == "check":
        d.line([x + 3, y + 12, x + 9, y + 19], fill=color, width=3)
        d.line([x + 9, y + 19, x + 21, y + 5], fill=color, width=3)
    elif name == "arrow":
        d.polygon(
            [x, y + 8, x + 14, y + 8, x + 14, y + 4, x + 24, y + 12, x + 14, y + 20, x + 14, y + 16, x, y + 16],
            fill=color,
        )
    elif name == "star":
        d.polygon(_star_points(x + 12, y + 12, 12, 5), fill=color)
    elif name == "bolt":
        d.polygon([x + 14, y, x + 6, y + 13, x + 12, y + 13, x + 10, y + 24, x + 18, y + 11, x + 12, y + 11], fill=color)
    elif name == "heart":
        d.ellipse([x + 2, y + 4, x + 13, y + 15], fill=color)
        d.ellipse([x + 11, y + 4, x + 22, y + 15], fill=color)
        d.polygon([x + 2, y + 10, x + 12, y + 22, x + 22, y + 10], fill=color)
    elif name == "lock":
        d.rectangle([x + 4, y + 11, x + 20, y + 23], fill=color)
        d.arc([x + 6, y + 2, x + 18, y + 14], 180, 0, fill=color, width=3)
    else:
        d.ellipse([x, y, x + 24, y + 24], fill=color)


def render_frames(
    data: dict[str, Any],
    duration: float,
    fps: int = DEFAULT_FPS,
    global_frame_offset: int = 0,
    on_frame: Optional[Callable[[Image.Image, int], None]] = None,
) -> list[Image.Image]:
    """Render icon list with staggered entrance inside glass card, with wrapping and boundary protection."""
    total_frames = max(1, math.ceil(duration * fps))
    heading_text = str(data.get("heading") or "").strip()
    raw_items = data.get("items", [])
    items = raw_items[:5]

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    card_x = 36 if ratio == "9:16" else 70
    card_y = 50 if ratio == "9:16" else 60
    card_w = w - (card_x * 2)
    card_h = h - (card_y * 2)

    heading_x = card_x + 32
    heading_y = card_y + 30
    max_heading_w = card_w - 64

    h2_size = 36 if ratio == "9:16" else (40 if ratio == "4:3" else 46)
    if ratio == "9:16":
        body_size = 24
    elif ratio == "4:3":
        body_size = 26
    else:
        body_size = 32 if len(items) <= 3 else 28

    font_heading = load_font(bold=True, size=h2_size)
    heading_lines = wrap_text(heading_text, font_heading, max_heading_w) if heading_text else []
    h_line_h = int(h2_size * 1.25)
    total_h_h = len(heading_lines) * h_line_h

    icon_w = 26
    text_x = heading_x + icon_w + 16
    max_item_text_w = (card_x + card_w - 36) - text_x

    parsed_items = []
    for it in items:
        if isinstance(it, dict):
            parsed_items.append((it.get("icon", "circle"), str(it.get("text", "")).strip()))
        else:
            parsed_items.append(("circle", str(it).strip()))

    avail_h = card_h - 100
    while body_size >= 18:
        font_item = load_font(bold=False, size=body_size)
        item_line_h = int(body_size * 1.35)
        wrapped_items = [wrap_text(txt, font_item, max_item_text_w) for _, txt in parsed_items]
        total_lines = sum(max(1, len(wl)) for wl in wrapped_items)
        n = max(1, len(parsed_items))
        gap = max(12, min(32, (avail_h - total_lines * item_line_h) // max(1, n)))
        needed_h = total_lines * item_line_h + (n - 1) * gap
        if needed_h <= avail_h or body_size <= 18:
            break
        body_size -= 2

    # Vertical centering inside card
    total_items_h = sum(max(1, len(wl)) * item_line_h for wl in wrapped_items) + (max(1, len(wrapped_items)) - 1) * gap
    total_content_h = total_h_h + (24 if heading_lines else 0) + total_items_h
    top_pad = max(30, (card_h - total_content_h) // 2) if card_h > total_content_h + 40 else 30

    heading_y = card_y + top_pad
    items_start_y = heading_y + total_h_h + (28 if heading_lines else 0)

    item_offsets: list[int] = []
    item_heights: list[int] = []
    cur_y = items_start_y
    for wl in wrapped_items:
        item_offsets.append(cur_y)
        ih = max(1, len(wl)) * item_line_h
        item_heights.append(ih)
        cur_y += ih + gap

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)

        draw_glass_card(canvas, card_x, card_y, card_w, card_h, radius=18)
        draw = ImageDraw.Draw(canvas)

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

        n_items = max(1, len(parsed_items))
        reveal_window = min(max(1.0, duration * 0.65), 1.2 * n_items)
        step = reveal_window / n_items

        for i, ((icon_name, _), wl, item_y, ih) in enumerate(zip(parsed_items, wrapped_items, item_offsets, item_heights)):
            item_start = 0.25 + i * step
            if t < item_start:
                continue

            item_p = min(1.0, (t - item_start) / 0.35)
            e = ease_out_cubic(item_p)
            slide_x = int(20 * (1.0 - e))

            cur_item_y = item_y
            cur_icon_x = heading_x + slide_x
            cur_text_x = text_x + slide_x

            # Draw icon
            draw_icon(draw, icon_name, cur_icon_x, cur_item_y + 2, hex_to_rgba(PALETTE["accent1"], e))

            # Draw multi-line text
            t_col = hex_to_rgba(PALETTE["text_hi"], e)
            for li, line in enumerate(wl):
                ly = cur_item_y + li * item_line_h
                draw_text_shadowed(
                    draw,
                    (cur_text_x, ly),
                    line,
                    font_item,
                    t_col,
                )

        canvas = apply_grain(canvas, strength=0.015, frame_idx=f)
        out_f = canvas.convert("RGB")
        if on_frame is not None:
            on_frame(out_f, f)
        else:
            frames.append(out_f)

    return frames
