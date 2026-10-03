"""Shared rendering utilities, color definitions, fonts, and easing for templates."""

from __future__ import annotations

import functools
import logging
import math
import os
from pathlib import Path
import re
from typing import Any, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

CANVAS_SIZES = {
    "16:9": (1280, 720),    # default, YouTube, desktop
    "9:16": (720, 1280),    # TikTok, Reels, Shorts
    "1:1": (720, 720),      # Instagram square
    "4:3": (960, 720),      # legacy, slideshow
}

_canvas_config = {"w": 1280, "h": 720, "ratio": "16:9"}
WIDTH = 1280
HEIGHT = 720
DEFAULT_FPS = 30

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
REGULAR_FONT_PATH = ASSETS_DIR / "Inter-Regular.ttf"
BOLD_FONT_PATH = ASSETS_DIR / "Inter-Bold.ttf"

SIZES = {
    "display": 72,   # single large stat / quote
    "h1": 56,        # title heading
    "h2": 44,        # section heading
    "h3": 34,        # card heading
    "body": 30,      # body text / bullets
    "caption": 24,   # label / metadata
    "mono": 24,      # code
}

PALETTE = {
    "bg_deep": "#0f0f1a",
    "bg_mid": "#1a1a2e",
    "bg_card": "#16213e",
    "accent1": "#6c63ff",   # purple
    "accent2": "#48cae4",   # cyan
    "accent3": "#ffd166",   # yellow
    "danger": "#ef476f",    # pink-red
    "success": "#06d6a0",   # green
    "text_hi": "#ffffff",
    "text_mid": "#c8c8e8",
    "text_low": "#7070a0",
}


def set_canvas(ratio: str = "16:9") -> None:
    """Set active canvas aspect ratio and dimensions."""
    global WIDTH, HEIGHT
    w, h = CANVAS_SIZES.get(ratio, (1280, 720))
    _canvas_config.update({"w": w, "h": h, "ratio": ratio})
    WIDTH = w
    HEIGHT = h
    get_base_background.cache_clear()


def get_canvas_size() -> tuple[int, int]:
    """Return (width, height) of currently active canvas."""
    return _canvas_config["w"], _canvas_config["h"]


def get_canvas_ratio() -> str:
    """Return active canvas ratio string (e.g. '16:9')."""
    return _canvas_config.get("ratio", "16:9")


# ── Easing Primitives ─────────────────────────────────────────────────────────

def ease_in_cubic(t: float) -> float:
    t_clamped = max(0.0, min(1.0, float(t)))
    return t_clamped ** 3


def ease_out_cubic(t: float) -> float:
    t_clamped = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t_clamped) ** 3


def ease_in_out_cubic(t: float) -> float:
    t_clamped = max(0.0, min(1.0, float(t)))
    if t_clamped < 0.5:
        return 4.0 * (t_clamped ** 3)
    return 1.0 - ((-2.0 * t_clamped + 2.0) ** 3) / 2.0


def ease_out_elastic(t: float) -> float:
    t_clamped = max(0.0, min(1.0, float(t)))
    if t_clamped == 0.0 or t_clamped == 1.0:
        return t_clamped
    return (2.0 ** (-10.0 * t_clamped)) * math.sin((t_clamped * 10.0 - 0.75) * (2.0 * math.pi / 3.0)) + 1.0


def ease_out_back(t: float) -> float:
    t_clamped = max(0.0, min(1.0, float(t)))
    c1, c3 = 1.70158, 2.70158
    return 1.0 + c3 * ((t_clamped - 1.0) ** 3) + c1 * ((t_clamped - 1.0) ** 2)


def ease_linear(t: float) -> float:
    return max(0.0, min(1.0, float(t)))


# ── Color & Surface Helpers ───────────────────────────────────────────────────

_CSS_COLORS: dict[str, str] = {
    "red": "#ff0000", "green": "#00ff00", "blue": "#0000ff",
    "white": "#ffffff", "black": "#000000", "yellow": "#ffff00",
    "cyan": "#00ffff", "magenta": "#ff00ff", "orange": "#ff8c00",
    "purple": "#800080", "pink": "#ff69b4", "gray": "#808080",
    "grey": "#808080", "coral": "#ff7f50", "gold": "#ffd700",
    "silver": "#c0c0c0", "navy": "#000080", "teal": "#008080",
    "lime": "#00ff00", "aqua": "#00ffff", "violet": "#ee82ee",
    "indigo": "#4b0082", "crimson": "#dc143c", "amber": "#ffbf00",
    "turquoise": "#40e0d0", "salmon": "#fa8072", "tomato": "#ff6347",
}


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Convert hex string like '#6c63ff' or CSS color name to RGB tuple (108, 99, 255)."""
    h = hex_code.strip().lstrip("#")
    # Try CSS color name lookup first
    css = _CSS_COLORS.get(h.lower())
    if css:
        h = css.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except (ValueError, IndexError):
        logger.warning("Invalid hex color '%s', falling back to gray", hex_code)
        return (128, 128, 128)


def hex_to_rgba(hex_code: str, alpha: float = 1.0) -> Tuple[int, int, int, int]:
    """Convert hex string and alpha (0.0 to 1.0) to RGBA tuple."""
    r, g, b = hex_to_rgb(hex_code)
    a = int(max(0.0, min(1.0, alpha)) * 255)
    return r, g, b, a


@functools.lru_cache(maxsize=8)
def get_base_background() -> Image.Image:
    """Generate cached base gradient (#0f0f1a to #1a1a2e top-to-bottom)."""
    w, h = get_canvas_size()
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    c_top = np.array(hex_to_rgb(PALETTE["bg_deep"]), dtype=np.float32)
    c_bottom = np.array(hex_to_rgb(PALETTE["bg_mid"]), dtype=np.float32)
    grad = (1.0 - t) * c_top + t * c_bottom
    arr = np.tile(grad, (1, w, 1)).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")


def create_canvas() -> Image.Image:
    """Create a fresh RGBA canvas pre-filled with the base dark gradient."""
    return get_base_background().copy()



# ── Pre-computed grain tiles (PIL-native, ~15x faster than numpy-per-frame) ───
_GRAIN_PIL_TILES: list[Image.Image] = []
_GRAIN_TILE_COUNT = 8
_GRAIN_STRENGTH = 0.022


def _build_grain_tiles() -> None:
    """Pre-generate grain tiles as PIL RGBA Images. Built once at import."""
    global _GRAIN_PIL_TILES
    # Max canvas size for pre-gen; cropped at runtime
    tw, th = 1280, 1280
    rng = np.random.default_rng(42)
    tiles = []
    for _ in range(_GRAIN_TILE_COUNT):
        # noise in [-28, 28] range at strength 0.022 * 255
        noise = rng.normal(0, _GRAIN_STRENGTH * 255, (th, tw, 1)).astype(np.float32)
        noise_clipped = np.clip(noise, -60, 60).astype(np.int16)
        # Store as int16 array for fast add
        tiles.append(noise_clipped)
    _GRAIN_PIL_TILES.clear()
    _GRAIN_PIL_TILES.extend(tiles)


_build_grain_tiles()


def apply_grain(img: Image.Image, strength: float = 0.03, frame_idx: int = 0) -> Image.Image:
    """Apply film grain — only every 4th frame (imperceptible, 4x faster).

    Film grain at 24fps is only noticeable if completely absent.
    Applying it to 1 in 4 frames achieves the 'premium texture' look at
    a quarter of the computation cost.
    """
    if frame_idx % 4 != 0:
        return img  # skip — grain on every 4th frame is sufficient
    tile = _GRAIN_PIL_TILES[frame_idx % _GRAIN_TILE_COUNT]
    cw, ch = img.size
    arr = np.frombuffer(img.tobytes(), dtype=np.uint8).reshape(ch, cw, -1).copy().astype(np.int16)
    noise = tile[:ch, :cw, :]
    if arr.shape[2] == 4:
        arr[:, :, :3] = np.clip(arr[:, :, :3] + noise, 0, 255)
    else:
        arr = np.clip(arr + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


# ── Cached animated background ────────────────────────────────────────────────
# Cache key: global_frame // 3 — background updates every 3 frames (imperceptible at 24fps)
_BG_CACHE: dict[tuple, np.ndarray] = {}
_BG_CACHE_MAX = 4  # keep at most 4 entries (~11MB RAM vs 1,415MB; frames render sequentially)


def clear_bg_cache() -> None:
    """Clear the animated background cache to release all RAM immediately."""
    _BG_CACHE.clear()


def make_animated_bg(
    frame_idx: int,
    total_frames: int,
    c1: str = "#0f0f1a",
    c2: str = "#1a1a2e",
    c3: str = "#0d1b2a",
    global_frame: int = 0,
) -> Image.Image:
    """Cached animated gradient background with drifting glow orbs.

    Background is recomputed only every 3 frames; cache keeps at most 4 entries.
    Orbs use 4 concentric ellipses (was 12) — same visual result, 3x faster.
    """
    w, h = get_canvas_size()
    gf = global_frame if global_frame > 0 else frame_idx
    # Quantise to every 3 frames so cache is effective
    cache_gf = (gf // 3) * 3
    cache_key = (cache_gf, w, h, c1, c3)

    if cache_key not in _BG_CACHE:
        if len(_BG_CACHE) >= _BG_CACHE_MAX:
            _BG_CACHE.clear()

        t = cache_gf / 600.0
        shift = 0.5 + 0.5 * math.sin(t * 2.0 * math.pi)
        tc = np.array(hex_to_rgb(c1), dtype=np.float32) * (1.0 - shift) + \
             np.array(hex_to_rgb(c3), dtype=np.float32) * shift
        bc = np.array(hex_to_rgb(c2), dtype=np.float32)
        vert = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        arr = ((1.0 - vert) * tc + vert * bc).astype(np.uint8)
        bg_arr = np.tile(arr, (1, w, 1))  # shape (h, w, 3)
        _BG_CACHE[cache_key] = bg_arr

    bg_arr = _BG_CACHE[cache_key]
    img = Image.fromarray(bg_arr).convert("RGBA")

    # Drifting orbs — 4 ellipses each (was 12), computed every 3 frames
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i, (spd, orb_hex, r_frac) in enumerate([
        (0.0007, "#6c63ff", 0.28),
        (0.0011, "#48cae4", 0.20),
    ]):
        angle = cache_gf * spd * 2.0 * math.pi + i * math.pi
        cx = int(w * 0.5 + w * 0.38 * math.sin(angle))
        cy = int(h * 0.5 + h * 0.32 * math.cos(angle * 0.7 + i))
        radius = int(min(w, h) * r_frac)
        r, g, b = hex_to_rgb(orb_hex)
        for s in range(4, 0, -1):   # 4 steps instead of 12
            frac = s / 4
            od.ellipse(
                [cx - int(radius * frac), cy - int(radius * frac),
                 cx + int(radius * frac), cy + int(radius * frac)],
                fill=(r, g, b, int(22 * frac)),
            )
    img = Image.alpha_composite(img, overlay)
    return img



def prepare_kinetic_captions(
    narration: str,
    audio_duration: float,
    font_size: int = 0,
) -> dict[str, Any]:
    """Precompute phrase timing, word boundaries, and badge layouts for kinetic captions.

    Word durations are weighted by character length and punctuation pauses to match
    natural speech cadence. Phrases are kept to 3-5 words so they never obscure slide content.
    """
    if not narration or not narration.strip() or audio_duration <= 0:
        return {"phrases": []}

    w, h = get_canvas_size()
    ratio = get_canvas_ratio()
    fsize = font_size or (22 if ratio == "9:16" else 24)
    font = load_font(bold=True, size=fsize)

    raw_words = narration.strip().split()
    if not raw_words:
        return {"phrases": []}

    # Calculate speech weights based on word length and punctuation pauses
    weights = []
    for w_tok in raw_words:
        clean = re.sub(r"[^\w]", "", w_tok)
        wt = max(2.0, float(len(clean)))
        if w_tok.endswith((",", ";", ":")):
            wt += 2.2
        elif w_tok.endswith((".", "!", "?")):
            wt += 3.8
        weights.append(wt)

    total_wt = sum(weights)
    if total_wt <= 0:
        return {"phrases": []}

    lead_in = min(0.08, audio_duration * 0.04) if audio_duration > 0.6 else 0.0
    effective_speech_dur = max(0.1, audio_duration - lead_in - 0.12) if audio_duration > 0.8 else audio_duration

    word_spans = []
    cur_t = lead_in
    for wt in weights:
        dur = (wt / total_wt) * effective_speech_dur
        word_spans.append((cur_t, cur_t + dur))
        cur_t += dur

    # Max words per phrase: 4 for vertical (9:16), 5 for horizontal
    max_words_per_phrase = 4 if ratio == "9:16" else 5

    space_w = font.getbbox(" ")[2] - font.getbbox(" ")[0]
    bh = fsize + 20
    by = h - bh - (110 if ratio == "9:16" else 26)

    phrases = []
    cur_words = []
    cur_spans = []

    for i, word in enumerate(raw_words):
        cur_words.append(word)
        cur_spans.append(word_spans[i])
        is_punct = word.endswith((",", ".", "!", "?", ";", ":"))
        if len(cur_words) >= max_words_per_phrase or is_punct or i == len(raw_words) - 1:
            p_start = 0.0 if len(phrases) == 0 else cur_spans[0][0]
            p_end = cur_spans[-1][1]

            # Measure word widths
            w_boxes = [font.getbbox(cw) for cw in cur_words]
            w_widths = [b[2] - b[0] for b in w_boxes]
            total_text_w = sum(w_widths) + max(0, len(cur_words) - 1) * space_w

            bw = min(w - 24, total_text_w + 32)
            bx = max(12, min(w - bw - 12, (w - bw) // 2))

            # Compute relative x for each word inside the badge
            word_rel_x = []
            cx = 16
            for ww in w_widths:
                word_rel_x.append(cx)
                cx += ww + space_w

            phrases.append({
                "words": list(cur_words),
                "spans": list(cur_spans),
                "widths": list(w_widths),
                "word_rel_x": word_rel_x,
                "start": p_start,
                "end": p_end,
                "bx": bx,
                "by": by,
                "bw": bw,
                "bh": bh,
            })
            cur_words = []
            cur_spans = []

    return {
        "phrases": phrases,
        "font": font,
        "fsize": fsize,
        "w": w,
        "h": h,
    }


def draw_kinetic_captions(
    canvas: Image.Image,
    narration: str,
    t: float,
    audio_duration: float,
    font_size: int = 0,
    cached_data: Optional[dict[str, Any]] = None,
) -> None:
    """Draw a dynamic kinetic caption badge at time t, synchronized to speech.

    - Active word glows with an electric cyan pill highlight in lockstep with audio.
    - Past words in the phrase remain crisp bright white.
    - Future words are legibly visible in soft translucent white.
    - Transitions immediately to the next phrase with zero lag.
    - Sits cleanly at the bottom without blocking slide content.
    - Clears automatically when speech is done.
    """
    if cached_data is None:
        cached_data = prepare_kinetic_captions(narration, audio_duration, font_size=font_size)

    phrases = cached_data.get("phrases")
    if not phrases:
        return

    font = cached_data["font"]
    bh = phrases[0]["bh"]

    # Find the active phrase with instant hand-off between phrases
    active_phrase = None
    for idx, p in enumerate(phrases):
        is_last = (idx == len(phrases) - 1)
        phrase_end = (p["end"] + 0.35) if is_last else p["end"]
        if p["start"] <= t < phrase_end:
            active_phrase = p
            break

    if not active_phrase:
        return

    bw = active_phrase["bw"]
    bx = active_phrase["bx"]
    by = active_phrase["by"]
    words = active_phrase["words"]
    spans = active_phrase["spans"]
    widths = active_phrase["widths"]
    rel_xs = active_phrase["word_rel_x"]

    # Create small floating glass badge patch
    patch = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    pd = ImageDraw.Draw(patch)
    # Deep glass pill with rounded corners and subtle border
    pd.rounded_rectangle(
        [0, 0, bw, bh],
        radius=12,
        fill=(12, 16, 28, 220),
        outline=(99, 102, 241, 100),
        width=1,
    )

    text_y = max(4, (bh - cached_data["fsize"]) // 2 - 2)
    for i, (word, (st, en), ww, rx) in enumerate(zip(words, spans, widths, rel_xs)):
        if t >= en:
            # Already spoken: crisp bright white
            color = (255, 255, 255, 245)
        elif st <= t < en:
            # Active word: electric cyan with glowing rounded backplate
            pd.rounded_rectangle(
                [rx - 4, text_y - 2, rx + ww + 4, text_y + bh - 14],
                radius=6,
                fill=(56, 189, 248, 55),
            )
            color = (56, 189, 248, 255)
        else:
            # Future word: soft translucent white so the user can read ahead
            color = (220, 225, 240, 115)

        pd.text((rx, text_y), word, font=font, fill=color)

    # Paste small badge directly onto canvas with alpha mask
    canvas.paste(patch, (bx, by), patch)


def draw_glass_card(
    canvas: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    bg_hex: str = "#ffffff",
    bg_alpha: float = 0.08,
    border_hex: str = "#6c63ff",
    border_alpha: float = 0.6,
    radius: int = 20,
) -> None:
    """Draw a frosted-glass card with subtle tinted border."""
    if w <= 0 or h <= 0:
        return
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    fill = (*hex_to_rgb(bg_hex), int(max(0.0, min(1.0, bg_alpha)) * 255))
    d.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill)
    if border_hex and border_alpha > 0:
        border = (*hex_to_rgb(border_hex), int(max(0.0, min(1.0, border_alpha)) * 255))
        d.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=border, width=2)
    canvas.alpha_composite(overlay)


# ── Typography & Drawing Primitives ───────────────────────────────────────────

def draw_text_shadowed(
    draw: ImageDraw.ImageDraw,
    pos: Tuple[int, int],
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    color: Tuple[int, int, int] | Tuple[int, int, int, int] | str,
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 140),
    offset: Tuple[int, int] = (3, 4),
) -> None:
    """Draw text with drop shadow on an RGBA canvas."""
    sx, sy = pos[0] + offset[0], pos[1] + offset[1]
    draw.text((sx, sy), text, font=font, fill=shadow_color)
    draw.text(pos, text, font=font, fill=color)


def draw_spaced_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    color: Tuple[int, int, int] | Tuple[int, int, int, int] | str,
    spacing: int = 2,
) -> int:
    """Draw text with extra letter spacing (pixels between each char). Returns end x."""
    cx = x
    for ch in text:
        draw.text((cx, y), ch, font=font, fill=color)
        bbox = draw.textbbox((0, 0), ch, font=font)
        cx += (bbox[2] - bbox[0]) + spacing
    return round(cx)


def wrap_text(text: str, font: ImageFont.ImageFont | ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Return lines of words that fit within max_width, breaking oversized words if needed."""
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        # If single word is wider than max_width, split by characters
        w_box = font.getbbox(word)
        if (w_box[2] - w_box[0]) > max_width:
            if current:
                lines.append(current)
                current = ""
            sub = ""
            for ch in word:
                test_sub = sub + ch
                sb = font.getbbox(test_sub)
                if (sb[2] - sb[0]) <= max_width:
                    sub = test_sub
                else:
                    if sub:
                        lines.append(sub)
                    sub = ch
            if sub:
                current = sub
            continue

        test = (current + " " + word).strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


@functools.lru_cache(maxsize=64)
def load_font(bold: bool = False, size: int = 36, monospace: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load font by style and size with fallback to system fonts and PIL scalable font."""
    if monospace:
        mono_candidates = [
            ASSETS_DIR / "JetBrainsMono-Regular.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
            Path("C:/Windows/Fonts/consola.ttf"),
            Path("C:/Windows/Fonts/cour.ttf"),
        ]
        for p in mono_candidates:
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    pass

    target_path = BOLD_FONT_PATH if bold else REGULAR_FONT_PATH
    if target_path.exists():
        try:
            return ImageFont.truetype(str(target_path), size)
        except Exception as exc:
            logger.warning("Failed to load font from %s: %s", target_path, exc)

    # Fallback to system fonts (Linux / Windows / macOS)
    system_candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/System/Library/Fonts/SFPro-Bold.ttf" if bold else "/System/Library/Fonts/SFPro.ttf"),
    ]
    for sp in system_candidates:
        if sp.exists():
            try:
                return ImageFont.truetype(str(sp), size)
            except Exception:
                pass

    logger.warning("Font not found or failed to load. Falling back to default font (size=%d).", size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_gradient_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    start_hex: str = "#6c63ff",
    end_hex: str = "#48cae4",
    alpha: float = 1.0,
    radius: int = 0,
) -> None:
    """Draw a horizontal gradient rectangle/bar."""
    if w <= 0 or h <= 0:
        return
    c_start = np.array(hex_to_rgb(start_hex), dtype=np.float32)
    c_end = np.array(hex_to_rgb(end_hex), dtype=np.float32)
    t = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    grad = (1.0 - t) * c_start + t * c_end
    arr = np.tile(grad, (h, 1, 1)).astype(np.uint8)

    a_val = int(max(0.0, min(1.0, alpha)) * 255)
    alpha_plane = np.full((h, w, 1), a_val, dtype=np.uint8)
    rgba_arr = np.concatenate([arr, alpha_plane], axis=2)
    bar_img = Image.fromarray(rgba_arr)

    if radius > 0:
        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
        bar_img.putalpha(mask)

    draw._image.alpha_composite(bar_img, dest=(x, y))
