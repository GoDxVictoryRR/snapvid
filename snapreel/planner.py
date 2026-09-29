"""Planner module for SnapReel.

Prepares user prompts and orchestrates video script generation,
including self-healing validation and optional quality critic pass.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from snapreel.llm import generate_scene_script
from snapreel.quality import quality_pass
from snapreel.schema import SceneScript

logger = logging.getLogger(__name__)


def build_prompt(topic: str) -> str:
    """Build the user prompt for the LLM scene planner.

    Args:
        topic: Video topic or subject matter.

    Returns:
        Non-empty prompt string containing the topic.

    Raises:
        ValueError: If topic is empty or only whitespace.
    """
    if not topic or not str(topic).strip():
        raise ValueError("Topic must be a non-empty string")

    clean_topic = str(topic).strip()
    return f"Create an engaging explainer video script on the topic: {clean_topic}"


def generate(
    topic: str,
    max_retries: int = 3,
    on_event: Optional[Callable[[dict[str, Any]], None]] = None,
    quality_review: Optional[bool] = None,
) -> SceneScript:
    """Generate a validated SceneScript for the specified topic.

    Calls generate_scene_script from snapreel.llm and runs quality_pass.

    Args:
        topic: Topic for the explainer video.
        max_retries: Maximum generation and validation repair attempts.
        on_event: Optional callback to stream agent activity events.
        quality_review: Explicit toggle for quality critic pass.

    Returns:
        Validated (and optionally critiqued) SceneScript instance.
    """
    prompt = build_prompt(topic)
    logger.info("Generating script for topic: %s", topic)

    t0 = time.perf_counter()
    script = generate_scene_script(prompt, max_retries=max_retries, on_event=on_event)
    duration = time.perf_counter() - t0

    # Run second quality critic pass
    script = quality_pass(
        script,
        on_event=on_event,
        enabled=quality_review,
        prev_duration=duration,
    )
    return script


__all__ = [
    "build_prompt",
    "generate",
]
