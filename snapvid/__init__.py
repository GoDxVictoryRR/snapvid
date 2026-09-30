"""SnapVid — Agentic Explainer-Video Maker.

This module provides the SnapVid package interface, mapping to the snapreel engine.
"""

from __future__ import annotations

import sys
import snapreel
from snapreel import planner, renderer, schema, llm, tts, server, quality, history, npu, transitions

__version__ = "0.1.0"

# Re-export key functions
__all__ = [
    "planner",
    "renderer",
    "schema",
    "llm",
    "tts",
    "server",
    "quality",
    "history",
    "npu",
    "transitions",
    "__version__",
]
