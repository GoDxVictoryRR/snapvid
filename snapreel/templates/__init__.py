"""SnapReel scene rendering templates."""

from snapreel.templates import (
    bar_chart,
    bullets,
    code_block,
    counter,
    icon_list,
    kinetic,
    lower_third,
    quote,
    split,
    title,
)

TEMPLATES = {
    "title": title,
    "bullets": bullets,
    "bar_chart": bar_chart,
    "counter": counter,
    "code_block": code_block,
    "kinetic": kinetic,
    "lower_third": lower_third,
    "quote": quote,
    "icon_list": icon_list,
    "split": split,
}

__all__ = [
    "title",
    "bullets",
    "bar_chart",
    "counter",
    "code_block",
    "kinetic",
    "lower_third",
    "quote",
    "icon_list",
    "split",
    "TEMPLATES",
]
