"""OpenAI-compatible LLM client and repair loop for SnapReel.

All LLM calls in SnapReel flow through llm_complete().
generate_scene_script() orchestrates prompt creation, schema validation,
and a self-correcting repair loop on invalid output while emitting agent events.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Optional

import dotenv
import requests
from pydantic import ValidationError

from snapreel.schema import SceneScript, validate_script

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

AgentEvent = dict[str, Any]  # {"type": str, "data": dict}


class LLMError(Exception):
    """Exception raised when an LLM call or script repair loop fails."""


PLANNER_SYSTEM_PROMPT = """You are a video script planner. Given a topic, output ONLY valid JSON matching
the SnapReel scene schema. No markdown fences, no explanation, just the JSON object.
Use 4 to 8 scenes. Keep narration concise and punchy.
Total video should be 30 to 90 seconds."""

REPAIR_PROMPT = """The previous JSON had this validation error:
{error}

Previous output:
{prev}

Output corrected JSON only. No explanation."""


def llm_complete(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """POST to {LLM_BASE_URL}/chat/completions. Returns content string.

    Args:
        prompt: User prompt content.
        system: Optional system instruction.
        temperature: Sampling temperature (default 0.3).

    Returns:
        Content string from LLM choices[0].message.content.

    Raises:
        LLMError: If LLM_BASE_URL/LLM_MODEL are missing, the HTTP request fails,
            or the response format is unexpected.
    """
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    if not base_url:
        raise LLMError("LLM_BASE_URL environment variable is not configured")

    model = os.environ.get("LLM_MODEL", "").strip()
    if not model:
        raise LLMError("LLM_MODEL environment variable is not configured")

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }

    timeout_sec = int(os.environ.get("LLM_TIMEOUT", 60))

    try:
        response = requests.post(url, json=body, headers=headers, timeout=timeout_sec)
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
    except requests.RequestException as exc:
        logger.error("LLM HTTP request failed: %s", exc)
        raise LLMError(f"LLM HTTP request failed: {exc}") from exc
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        logger.error("Unexpected LLM response format: %s", exc)
        raise LLMError(f"Unexpected LLM response format: {exc}") from exc


def llm_complete_timed(
    prompt: str, system: str = "", temperature: float = 0.3
) -> tuple[str, dict[str, Any]]:
    """Wrap llm_complete with precise latency and token throughput timing."""
    t0 = time.perf_counter()
    result = llm_complete(prompt, system, temperature)
    elapsed = max(0.001, time.perf_counter() - t0)
    tokens_approx = max(1, len(result.split()))
    logger.info(
        "LLM: ~%d tokens in %.2fs (~%.1f tok/s)",
        tokens_approx,
        elapsed,
        tokens_approx / elapsed,
    )
    return result, {"tokens": tokens_approx, "seconds": round(elapsed, 2)}


def generate_scene_script(
    topic: str,
    max_retries: int = 3,
    on_event: Optional[Callable[[AgentEvent], None]] = None,
) -> SceneScript:
    """Generate and validate a SceneScript for a given topic with a self-healing repair loop.

    Emits AgentEvents during each step of planning and validation.

    Args:
        topic: The subject matter for the video script.
        max_retries: Maximum number of generation attempts.
        on_event: Optional callback to stream agent activity events.

    Returns:
        Validated SceneScript instance.

    Raises:
        LLMError: If all retry attempts fail schema validation or LLM fails.
    """
    def emit(type_: str, **data: Any) -> None:
        if on_event:
            on_event({"type": type_, "data": data})

    emit("planning_start", topic=topic)
    last_error: Optional[Exception] = None
    response = ""
    prompt = topic

    for attempt in range(max_retries):
        if attempt > 0:
            prompt = REPAIR_PROMPT.format(error=last_error, prev=response)

        logger.info("Generating scene script attempt %d/%d", attempt + 1, max_retries)
        response = llm_complete(prompt=prompt, system=PLANNER_SYSTEM_PROMPT)
        emit("llm_response", attempt=attempt + 1, length=len(response))

        try:
            script = validate_script(response)
            emit("plan_accepted", scenes=len(script.scenes), attempt=attempt + 1)
            return script
        except ValidationError as exc:
            last_error = exc
            emit("plan_rejected", attempt=attempt + 1, error=str(exc))
            logger.warning("Validation failed on attempt %d: %s", attempt + 1, exc)

    emit("plan_failed", attempts=max_retries)
    raise LLMError(
        f"Failed to generate valid scene script after {max_retries} retries: {last_error}"
    )


def test_llm_connection(base_url: str, model: str, api_key: str = "") -> dict[str, Any]:
    """Test connectivity to an OpenAI-compatible LLM endpoint."""
    if not base_url or not model:
        return {"ok": False, "error": "base_url and model are required"}

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        resp.raise_for_status()
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {"ok": True, "model": model, "latency_ms": latency_ms}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


__all__ = [
    "AgentEvent",
    "LLMError",
    "PLANNER_SYSTEM_PROMPT",
    "REPAIR_PROMPT",
    "llm_complete",
    "llm_complete_timed",
    "generate_scene_script",
    "test_llm_connection",
]
