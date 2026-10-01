"""Scene-level quality critic agent for SnapReel.

Performs a secondary agent pass to critique and polish narration,
scene pacing, and data consistency.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from snapreel.llm import llm_complete
from snapreel.schema import SceneScript, validate_script

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """Review this video scene script. For each scene, check:
1. Is the narration under 200 chars? If not, shorten it.
2. Is the data appropriate for the template? (bar_chart needs numbers, etc.)
3. Is the scene duration reasonable for the content?

Return the improved script JSON only. No explanation.

Script:
{script_json}
"""


def quality_pass(
    script: SceneScript,
    on_event: Optional[Callable[[dict[str, Any]], None]] = None,
    enabled: Optional[bool] = None,
    prev_duration: Optional[float] = None,
    llm_config: Optional[dict[str, Any]] = None,
) -> SceneScript:
    """Optional second LLM pass to improve scene quality.

    Args:
        script: Validated SceneScript from planner.
        on_event: Optional callback for agent SSE activity events.
        enabled: Explicitly enable/disable; defaults to ENABLE_QUALITY_PASS env var (true).
        prev_duration: Latency of preceding LLM call in seconds (skipped if > 20s).
        llm_config: Optional per-request LLM configuration.

    Returns:
        Improved SceneScript or original if critic fails or is skipped.
    """
    def emit(type_: str, **data: Any) -> None:
        if on_event:
            on_event({"type": type_, "data": data})

    if enabled is None:
        env_val = os.environ.get("ENABLE_QUALITY_PASS", "true").strip().lower()
        enabled = env_val not in ("false", "0", "no", "off")

    if not enabled:
        emit("quality_skipped", reason="Quality pass disabled by configuration")
        return script

    if prev_duration is not None and prev_duration > 20.0:
        emit(
            "quality_skipped",
            reason=f"Previous LLM call took {prev_duration:.1f}s (>20s threshold)",
        )
        return script

    emit("quality_start", scenes=len(script.scenes))
    cfg = llm_config or {}
    try:
        raw = llm_complete(
            CRITIC_PROMPT.format(script_json=script.model_dump_json()),
            base_url=cfg.get("base_url"),
            model=cfg.get("model"),
            api_key=cfg.get("api_key"),
            timeout=cfg.get("timeout"),
        )
        improved = validate_script(raw)
        emit("quality_accepted", scenes=len(improved.scenes))
        logger.info("Quality pass accepted improved script with %d scenes", len(improved.scenes))
        return improved
    except Exception as exc:
        logger.warning("Quality pass rejected invalid output (%s); falling back to original", exc)
        emit("quality_rejected", error=str(exc))
        return script


__all__ = [
    "CRITIC_PROMPT",
    "quality_pass",
]
