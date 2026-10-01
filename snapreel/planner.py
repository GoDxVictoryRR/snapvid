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
import re
from snapreel.schema import SceneScript

logger = logging.getLogger(__name__)


def build_prompt(topic: str, target_duration: int = 60, aspect_ratio: str = "16:9") -> str:
    """Build the user prompt for the LLM scene planner."""
    if not topic or not topic.strip():
        raise ValueError("Topic must be a non-empty string")

    clean_topic = topic.strip()
    # Strip conflicting duration mentions like "in 60s" or "in 2 minutes" from topic
    clean_topic = re.sub(
        r"(?i)\s+in\s+\d+\s*(?:s|sec|secs|seconds?|min|mins|minutes?)\s*\??\s*$",
        "",
        clean_topic,
    )
    return (
        f"Create an engaging explainer video script on the topic: {clean_topic}. "
        f"Target video length: {target_duration} seconds. Aspect ratio: {aspect_ratio}.\n"
        f"CRITICAL: Output ONLY a single raw JSON object matching the schema. "
        f"Do NOT write any thinking process, reasoning steps, or conversational preamble. "
        f"Start directly with '{{' and end with '}}'."
    )


def generate(
    topic: str,
    max_retries: int = 3,
    on_event: Optional[Callable[[dict[str, Any]], None]] = None,
    quality_review: Optional[bool] = None,
    target_duration: int = 60,
    aspect_ratio: str = "16:9",
    llm_config: Optional[dict[str, Any]] = None,
) -> SceneScript:
    """Generate a validated SceneScript for the specified topic."""
    prompt = build_prompt(topic, target_duration=target_duration, aspect_ratio=aspect_ratio)
    logger.info("Generating script for topic: %s (target=%ds, ratio=%s)", topic, target_duration, aspect_ratio)

    t0 = time.perf_counter()
    script = generate_scene_script(
        prompt,
        max_retries=max_retries,
        on_event=on_event,
        target_duration=target_duration,
        llm_config=llm_config,
    )
    duration = time.perf_counter() - t0

    script.target_duration = target_duration
    script.aspect_ratio = aspect_ratio

    # Run second quality critic pass
    script = quality_pass(
        script,
        on_event=on_event,
        enabled=quality_review,
        prev_duration=duration,
        llm_config=llm_config,
    )
    script.target_duration = target_duration
    script.aspect_ratio = aspect_ratio
    return script


__all__ = [
    "build_prompt",
    "generate",
]
