"""Lower third scene template renderer."""

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
    ease_out_cubic,
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
    """Render lower third banner with slide-in animation from left, text width clamping, and fade out at end."""
    total_frames = max(1, math.ceil(duration * fps))
    name_text = str(data.get("name") or "").strip()
    role_text = str(data.get("role") or "").strip()
    accent_color = str(data.get("accent") or PALETTE["accent1"])

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()

    h3_size = 24 if ratio == "9:16" else SIZES["h3"]
    cap_size = 18 if ratio == "9:16" else SIZES["caption"]

    font_name = load_font(bold=True, size=h3_size)
    font_role = load_font(bold=False, size=cap_size)

    max_text_w = w - 70

    # Ensure name_text and role_text do not overflow right edge
    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)
    if (dd.textbbox((0, 0), name_text, font=font_name)[2] - dd.textbbox((0, 0), name_text, font=font_name)[0]) > max_text_w:
        while len(name_text) > 3 and (dd.textbbox((0, 0), name_text + "...", font=font_name)[2] - dd.textbbox((0, 0), name_text + "...", font=font_name)[0]) > max_text_w:
            name_text = name_text[:-1]
        name_text += "..."

    if (dd.textbbox((0, 0), role_text, font=font_role)[2] - dd.textbbox((0, 0), role_text, font=font_role)[0]) > max_text_w:
        while len(role_text) > 3 and (dd.textbbox((0, 0), role_text + "...", font=font_role)[2] - dd.textbbox((0, 0), role_text + "...", font=font_role)[0]) > max_text_w:
            role_text = role_text[:-1]
        role_text += "..."

    bar_h = 80 if ratio == "9:16" else 84
    bar_y = h - bar_h - (120 if ratio == "9:16" else 60)

    frames: list[Image.Image] = []

    for f in range(total_frames):
        t = f / fps
        canvas = make_animated_bg(f, total_frames, global_frame=global_frame_offset + f)

        # Entrance: slide in from left at t=0.4s over 0.4s
        in_p = max(0.0, min(1.0, (t - 0.4) / 0.4)) if duration > 0.4 else min(1.0, t / 0.2)
        in_e = ease_out_cubic(in_p)

        # Exit: fade out at last 0.5s of scene
        out_start = max(0.0, duration - 0.5)
        out_alpha = 1.0 - (max(0.0, (t - out_start) / 0.5)) if t >= out_start else 1.0
        alpha = in_e * out_alpha

        if alpha > 0.01:
            slide_x = int((1.0 - in_e) * -w)
            bar_x = slide_x

            # Semi-transparent dark banner
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            odraw = ImageDraw.Draw(overlay)
            odraw.rectangle([bar_x, bar_y, bar_x + w, bar_y + bar_h], fill=(15, 15, 26, int(230 * alpha)))

            # Left accent stripe: 6px wide, full bar height
            odraw.rectangle([bar_x, bar_y, bar_x + 6, bar_y + bar_h], fill=(*hex_to_rgba(accent_color, 1.0)[:3], int(255 * alpha)))

            # Name and role text
            text_x = bar_x + 36
            name_y = bar_y + 12
            role_y = bar_y + 48

            odraw.text(
                (text_x, name_y),
                name_text,
                font=font_name,
                fill=(*hex_to_rgba(PALETTE["text_hi"], 1.0)[:3], int(255 * alpha)),
            )
            odraw.text(
                (text_x, role_y),
                role_text,
                font=font_role,
                fill=(*hex_to_rgba(PALETTE["text_mid"], 1.0)[:3], int(230 * alpha)),
            )

            canvas.alpha_composite(overlay)

        canvas = apply_grain(canvas, strength=0.015, frame_idx=f)
        out_f = canvas.convert("RGB")
        if on_frame is not None:
            on_frame(out_f, f)
        else:
            frames.append(out_f)

    return frames
