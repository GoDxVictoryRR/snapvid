"""Session history tracking for SnapReel.

Maintains a lightweight local log of the last 5 generated videos.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HISTORY_FILE = Path("output/.history.json")


def load() -> list[dict[str, Any]]:
    """Load video generation history from local JSON file."""
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.warning("Failed to load history from %s: %s", HISTORY_FILE, exc)
    return []


def save(topic: str, output_path: str, scene_count: int) -> list[dict[str, Any]]:
    """Save a newly rendered video to history, keeping the 5 most recent."""
    history = load()
    entry = {
        "topic": topic,
        "path": output_path,
        "scenes": scene_count,
    }
    # Prepend new item
    history.insert(0, entry)
    history = history[:5]

    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to write history to %s: %s", HISTORY_FILE, exc)

    return history


__all__ = [
    "HISTORY_FILE",
    "load",
    "save",
]
