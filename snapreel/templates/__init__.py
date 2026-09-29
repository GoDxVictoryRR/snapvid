"""SnapReel scene rendering templates."""

from snapreel.templates import bar_chart, bullets, code_block, counter, kinetic, title

TEMPLATES = {
    "title": title,
    "bullets": bullets,
    "bar_chart": bar_chart,
    "counter": counter,
    "code_block": code_block,
    "kinetic": kinetic,
}

__all__ = [
    "title",
    "bullets",
    "bar_chart",
    "counter",
    "code_block",
    "kinetic",
    "TEMPLATES",
]
