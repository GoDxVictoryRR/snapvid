"""Shared rendering utilities, color definitions, fonts, and easing for templates."""

from __future__ import annotations

import functools
import logging
import os
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

WIDTH = 1280
HEIGHT = 720
DEFAULT_FPS = 30

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
REGULAR_FONT_PATH = ASSETS_DIR / "Inter-Regular.ttf"
BOLD_FONT_PATH = ASSETS_DIR / "Inter-Bold.ttf"


def ease_out_cubic(t: float) -> float:
    """Ease out cubic function: f(t) = 1 - (1 - t)^3 for t in [0, 1]."""
    t_clamped = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t_clamped) ** 3


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Convert hex string like '#6c63ff' to RGB tuple (108, 99, 255)."""
    h = hex_code.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hex_to_rgba(hex_code: str, alpha: float = 1.0) -> Tuple[int, int, int, int]:
    """Convert hex string and alpha (0.0 to 1.0) to RGBA tuple."""
    r, g, b = hex_to_rgb(hex_code)
    a = int(max(0.0, min(1.0, alpha)) * 255)
    return r, g, b, a


@functools.lru_cache(maxsize=1)
def get_base_background() -> Image.Image:
    """Generate cached 1280x720 base gradient (#0f0f1a to #1a1a2e top-to-bottom)."""
    t = np.linspace(0, 1, HEIGHT, dtype=np.float32)[:, None, None]
    c_top = np.array(hex_to_rgb("#0f0f1a"), dtype=np.float32)
    c_bottom = np.array(hex_to_rgb("#1a1a2e"), dtype=np.float32)
    grad = (1.0 - t) * c_top + t * c_bottom
    arr = np.tile(grad, (1, WIDTH, 1)).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")


def create_canvas() -> Image.Image:
    """Create a fresh RGBA canvas pre-filled with the base dark gradient."""
    return get_base_background().copy()


@functools.lru_cache(maxsize=32)
def load_font(bold: bool = False, size: int = 36, monospace: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load font by style and size with fallback to default PIL font."""
    if monospace:
        # Check standard Windows fonts or assets
        mono_candidates = [
            ASSETS_DIR / "JetBrainsMono-Regular.ttf",
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

    logger.warning("Font not found or failed to load. Falling back to default font.")
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
):
    """Draw a horizontal gradient rectangle/bar."""
    if w <= 0 or h <= 0:
        return
    c_start = np.array(hex_to_rgb(start_hex), dtype=np.float32)
    c_end = np.array(hex_to_rgb(end_hex), dtype=np.float32)
    t = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    grad = (1.0 - t) * c_start + t * c_end
    arr = np.tile(grad, (h, 1, 1)).astype(np.uint8)

    # Add alpha channel
    a_val = int(max(0.0, min(1.0, alpha)) * 255)
    alpha_plane = np.full((h, w, 1), a_val, dtype=np.uint8)
    rgba_arr = np.concatenate([arr, alpha_plane], axis=2)
    bar_img = Image.fromarray(rgba_arr)

    # Use a mask for rounded corners if radius > 0
    if radius > 0:
        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
        bar_img.putalpha(mask)

    draw._image.alpha_composite(bar_img, dest=(x, y))
