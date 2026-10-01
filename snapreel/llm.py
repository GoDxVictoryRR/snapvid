"""OpenAI-compatible LLM client and repair loop for SnapReel.

All LLM calls in SnapReel flow through llm_complete().
generate_scene_script() orchestrates prompt creation, schema validation,
and a self-correcting repair loop on invalid output while emitting agent events.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Callable, Optional

import dotenv  # type: ignore
import requests
from pydantic import ValidationError

from snapreel.schema import SceneScript, validate_script

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

AgentEvent = dict[str, Any]  # {"type": str, "data": dict}


class LLMError(Exception):
    """Exception raised when an LLM call or script repair loop fails."""


PLANNER_SYSTEM_PROMPT = """You are a video script planner. Output ONLY a single valid JSON object.
CRITICAL INSTRUCTIONS:
- Do NOT output any thinking process, chain-of-thought, reasoning notes, or conversational preamble (NEVER write "Here's a thinking process" or "Certainly!").
- Do NOT output markdown formatting outside the JSON.
- Your entire response MUST start immediately with the character '{' and end with '}'.

The JSON must match this exact schema:
{
  "title": "<video title, max 80 chars>",
  "total_duration": <sum of all scene durations as float>,
  "scenes": [
    {
      "id": "s1",
      "template": "title",
      "duration": 5.0,
      "narration": "Welcome to our deep dive into on-device artificial intelligence powered by dedicated NPU acceleration.",
      "data": {"heading": "On-Device AI Explained", "subheading": "Offline Intelligence on Snapdragon"}
    },
    {
      "id": "s2",
      "template": "bullets",
      "duration": 8.0,
      "narration": "Unlike cloud AI that suffers from latency and network dependency, on-device processing executes neural networks locally with complete privacy and zero data leakage.",
      "data": {"heading": "Core Advantages", "items": ["Zero Cloud Latency", "100% Offline Privacy", "Ultra-Low Power Consumption", "Always-Available Response"]}
    },
    {
      "id": "s3",
      "template": "bar_chart",
      "duration": 8.0,
      "narration": "Comparing inference latency across architectures shows the dedicated NPU delivering dramatic speed improvements over standard CPU and GPU execution.",
      "data": {"heading": "Inference Latency", "labels": ["CPU", "GPU", "NPU"], "values": [120, 45, 12], "unit": "ms"}
    }
  ]
}

Template rules — data field MUST be an object, never a string:
- title:       {"heading": str, "subheading": str or null}
- bullets:     {"heading": str, "items": [str, ...] (3-5 items, rich and informative)}
- bar_chart:   {"heading": str, "labels": [str,...], "values": [number,...], "unit": str or null (3-4 items)}
- counter:     {"label": str, "from": number, "to": number, "unit": str or null}
- code_block:  {"heading": str or null, "language": "python"|"js"|"bash"|"plain", "code": str}
- kinetic:     {"lines": [str, ...] (2-4 bold lines)}
- lower_third: {"name": str, "role": str or null, "accent": str or null}
- quote:       {"text": str, "author": str or null}
- icon_list:   {"heading": str, "items": [{"icon": str, "label": str}, ...] (3-5 items)}
- split:       {"left": str, "right": str, "heading": str or null}
Do NOT use "image" or any other template name. Use ONLY the 10 templates listed above.

Constraints: detailed voiceover narration matching scene duration (~2.7 words per second).
For a 10-second scene write at least 25 words of narration. For a 15-second scene write at least 38 words.

CRITICAL JSON RULES — failure to follow these will cause a parse error:
1. Separate every property in an object with a comma, EXCEPT after the last property.
2. Separate every element in an array with a comma, EXCEPT after the last element.
3. No trailing commas: NEVER write ,} or ,]
4. Use double quotes for all strings."""


def _build_system_prompt(target_duration: int = 60) -> str:
    """Build a system prompt optimized for local LLMs with balanced scene counts and rich narration."""
    if target_duration <= 30:
        min_scenes, max_scenes = 3, 5
    elif target_duration <= 60:
        min_scenes, max_scenes = 5, 7
    elif target_duration <= 90:
        min_scenes, max_scenes = 7, 10
    elif target_duration <= 120:
        min_scenes, max_scenes = 9, 13
    elif target_duration <= 180:
        min_scenes, max_scenes = 13, 17
    elif target_duration <= 300:
        min_scenes, max_scenes = 20, 26
    else:
        min_scenes = min(22, max(20, int(target_duration / 15)))
        max_scenes = min(28, max(min_scenes + 4, int(target_duration / 11)))

    # Target scene count at midpoint; avg_dur scales with target
    target_scenes = (min_scenes + max_scenes) // 2
    avg_dur = round(target_duration / target_scenes, 1)
    max_scene_dur = min(28.0, round(avg_dur * 1.6, 1))  # never exceed schema limit 30s
    words_per_scene = max(18, round(avg_dur * 2.7))

    return (
        PLANNER_SYSTEM_PROMPT
        + f"""

VIDEO SPECIFICATIONS:
- Target video length: {target_duration} seconds
- Recommended scene count: {min_scenes} to {max_scenes} scenes (average ~{avg_dur:.1f}s per scene)
- Each scene duration: between {max(5, round(avg_dur * 0.5)):.0f}s and {max_scene_dur:.0f}s (MUST NOT exceed 28s per scene, minimum 5s)
- total_duration: float, must be approximately {target_duration}.0
- Scene durations MUST sum to approximately {target_duration}s — distribute them across all scenes.

NARRATION & SLIDE CONTENT GUIDELINES:
- For every scene, write at least {words_per_scene} words of spoken narration so the voiceover fills the scene duration (target: ~2.7 words/second).
- For a {avg_dur:.0f}-second scene that means {words_per_scene}+ words — write 2 to 4 full, informative sentences.
- Populate templates with meaningful content:
  * bullets: 3–4 informative bullet points (not single words)
  * icon_list: 3–4 items with valid icons (circle, star, check, arrow, bolt, heart, lock) and descriptive labels
  * bar_chart: 3–4 items with real numeric values, labels, and unit
  * split: 1–2 explanatory sentences on the left
  * kinetic: 2–3 bold takeaway lines
- Output ONLY the single JSON object."""
    )

REPAIR_PROMPT = """Fix this error: {error}
Keep all scenes and durations intact. Output corrected JSON only. No explanation."""

REPAIR_PROMPT_DURATION = """Error: scene durations sum to {actual}s but must sum to {target}s.
Multiply each scene duration by {factor:.2f}. Set total_duration to {target}.0.
Output corrected JSON only."""

REPAIR_PROMPT_TOO_SHORT = """Error: script is only {actual}s but target is {target}s.
Add more scenes. Each scene duration must be between 8.0 and 25.0 seconds (NEVER exceed 28 seconds per scene).
total_duration must equal {target}.0. Output corrected JSON only."""


def llm_complete(
    prompt: str,
    system: str = "",
    temperature: float = 0.3,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
) -> str:
    """POST to {LLM_BASE_URL}/chat/completions. Returns content string.

    Args:
        prompt: User prompt content.
        system: Optional system instruction.
        temperature: Sampling temperature (default 0.3).
        base_url: Optional override for LLM_BASE_URL.
        model: Optional override for LLM_MODEL.
        api_key: Optional override for LLM_API_KEY.
        timeout: Optional override for LLM_TIMEOUT in seconds.

    Returns:
        Content string from LLM choices[0].message.content.

    Raises:
        LLMError: If LLM_BASE_URL/LLM_MODEL are missing, the HTTP request fails,
            or the response format is unexpected.
    """
    resolved_base_url = (base_url or os.environ.get("LLM_BASE_URL", "")).strip()
    if not resolved_base_url:
        raise LLMError("LLM_BASE_URL environment variable is not configured")
    if "generativelanguage.googleapis.com" in resolved_base_url and not resolved_base_url.rstrip("/").endswith("/openai"):
        resolved_base_url = resolved_base_url.rstrip("/") + "/openai"

    resolved_model = (model or os.environ.get("LLM_MODEL", "")).strip()
    if not resolved_model:
        raise LLMError("LLM_MODEL environment variable is not configured")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resolved_api_key = (api_key if api_key is not None else os.environ.get("LLM_API_KEY", "")).strip()
    if resolved_api_key:
        headers["Authorization"] = f"Bearer {resolved_api_key}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    body: dict[str, Any] = {
        "model": resolved_model,
        "temperature": temperature,
        "messages": messages,
    }

    # Route Ollama local calls to native /api/chat with think=False to disable
    # expensive reasoning loops on local thinking models (Granite, Nemotron, Qwen, DeepSeek).
    if ":11434" in resolved_base_url:
        url = resolved_base_url.split("/v1")[0].rstrip("/") + "/api/chat"
        body["think"] = False
        body["stream"] = False
    else:
        url = resolved_base_url.rstrip("/") + "/chat/completions"
        body["stream"] = False
        body["top_p"] = 1.0
        # Explicit max_tokens prevents gateway buffer errors; 8192 provides ample space for 90s-180s scripts
        body["max_tokens"] = int(os.environ.get("LLM_MAX_TOKENS", 8192))

    timeout_sec = timeout if timeout is not None else int(os.environ.get("LLM_TIMEOUT", 360))

    # Pre-flight: verify model is available locally (fast, avoids 60s+ auto-pull hangs)
    _assert_model_available(resolved_base_url, resolved_model, headers)

    max_http_retries = 3
    is_test_env = "fake" in resolved_base_url or "test" in resolved_base_url

    for http_attempt in range(max_http_retries):
        current_body = dict(body)

        # Adaptive strategy for NVIDIA NIM / cloud proxy gateways that fail on 'system' role or buffer limits:
        # On attempt 1: if system is present and endpoint had an issue, combine system prompt into user prompt
        if http_attempt == 1 and system:
            current_body["messages"] = [
                {"role": "user", "content": f"{system}\n\nTask:\n{prompt}"}
            ]
            logger.info("Retrying LLM call with combined system-user prompt format...")

        try:
            response = requests.post(url, json=current_body, headers=headers, timeout=timeout_sec)
            response.raise_for_status()
            payload = response.json()
            if "choices" in payload and payload["choices"]:
                choice = payload["choices"][0]
                msg = choice.get("message", {})
            elif "message" in payload:
                msg = payload["message"]
            else:
                msg = {}
            content = msg.get("content")
            # Handle reasoning models (e.g. Qwen3.5, DeepSeek R1) that place generation in reasoning
            if not content and "reasoning" in msg:
                content = msg.get("reasoning")
            if not content and "reasoning_content" in msg:
                content = msg.get("reasoning_content")
            if content is None:
                content = ""
            # Strip <think>...</think> tags if returned by reasoning models
            if content and "<think>" in content.lower():
                content = re.sub(r"(?is)<think>.*?</think>", "", content).strip()
            return content
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            if status_code == 0:
                m = re.search(r"\b(429|500|502|503|504)\b", str(exc))
                if m:
                    status_code = int(m.group(1))
            detail = ""
            if exc.response is not None:
                try:
                    detail = f" (Details: {exc.response.text.strip()[:200]})"
                except Exception:
                    pass
            # Retry transient server errors (429, 500, 502, 503, 504)
            if status_code in (429, 500, 502, 503, 504) and http_attempt < max_http_retries - 1:
                wait_sec = 0.0 if is_test_env else (http_attempt + 1) * 2.0
                logger.warning(
                    "LLM HTTP %d on %s%s; retrying in %.1fs (attempt %d/%d)...",
                    status_code, url, detail, wait_sec, http_attempt + 1, max_http_retries
                )
                if wait_sec > 0:
                    time.sleep(wait_sec)
                continue
            err_msg = f"LLM HTTP request failed: {exc}{detail}"
            if "500" in str(exc) and "localhost:11434" in url:
                err_msg += " -> Ollama internal error (model exceeds VRAM or crashed). Try a lighter model like 'nemotron-3-nano:4b' or check Ollama logs."
            logger.error(err_msg)
            raise LLMError(err_msg) from exc
        except requests.RequestException as exc:
            if http_attempt < max_http_retries - 1:
                wait_sec = 0.0 if is_test_env else 2.0
                if wait_sec > 0:
                    time.sleep(wait_sec)
                continue
            err_msg = f"LLM HTTP request failed: {exc}"
            logger.error(err_msg)
            raise LLMError(err_msg) from exc
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


def _pre_heal_llm_json(text: str, target_duration: int = 0) -> str:
    """Pre-heal common LLM output imperfections and proportionally scale durations to target."""
    import json
    try:
        from snapreel.schema import _repair_json
        cleaned = _repair_json(text.strip())
        data = json.loads(cleaned)
        if isinstance(data, dict) and "scenes" in data and isinstance(data["scenes"], list):
            dur_sum = 0.0
            valid_scenes = []
            for s in data["scenes"]:
                if isinstance(s, dict):
                    tmpl = str(s.get("template", "")).lower().strip()
                    if tmpl in ("image", "diagram", "graphic", "visual", "photo", "slide", "figure"):
                        s["template"] = "bullets"
                        if not isinstance(s.get("data"), dict) or "items" not in s["data"]:
                            s["data"] = {"heading": "Key Points", "items": ["Core concept", "Essential takeaway"]}
                    if "duration" in s:
                        try:
                            d_val = float(s["duration"])
                            # Clamp duration to schema limits [3.0, 30.0]
                            d_val = min(30.0, max(3.0, d_val))
                            s["duration"] = round(d_val, 2)
                            dur_sum += s["duration"]
                            valid_scenes.append(s)
                        except (ValueError, TypeError):
                            pass
            if target_duration and target_duration > 0 and dur_sum >= target_duration * 0.45 and valid_scenes:
                # Proportional scaling to match target_duration exactly
                scale = target_duration / dur_sum
                new_sum = 0.0
                for s in valid_scenes:
                    d_scaled = min(30.0, max(3.0, round(float(s["duration"]) * scale, 2)))
                    s["duration"] = d_scaled
                    new_sum += d_scaled
                diff = round(target_duration - new_sum, 2)
                valid_scenes[-1]["duration"] = round(max(3.0, valid_scenes[-1]["duration"] + diff), 2)
                data["total_duration"] = float(target_duration)
                return json.dumps(data)
            elif dur_sum > 0:
                data["total_duration"] = round(dur_sum, 2)
                return json.dumps(data)
    except Exception:
        pass
    return text


def generate_scene_script(
    topic: str,
    max_retries: int = 3,
    on_event: Optional[Callable[[AgentEvent], None]] = None,
    target_duration: int = 60,
    llm_config: Optional[dict[str, Any]] = None,
) -> SceneScript:
    """Generate and validate a SceneScript for a given topic with a self-healing repair loop."""
    def emit(type_: str, **data: Any) -> None:
        if on_event:
            on_event({"type": type_, "data": data})

    system_prompt = _build_system_prompt(target_duration)
    emit("planning_start", topic=topic)
    last_error: Optional[Exception] = None
    response = ""
    prompt = topic
    cfg = llm_config or {}

    for attempt in range(max_retries):
        if attempt > 0:
            err_str = str(last_error)
            # Choose targeted repair prompt based on error type
            if "total_duration mismatch" in err_str or "sum of scene durations" in err_str:
                m = re.search(r"sum of scene durations is (\d+\.?\d*)", err_str)
                actual_sum = float(m.group(1)) if m else target_duration * 0.5
                factor = target_duration / actual_sum if actual_sum > 0 else 1.0
                prompt = REPAIR_PROMPT_DURATION.format(
                    error=err_str,
                    prev=response,
                    target=target_duration,
                    actual=actual_sum,
                    factor=factor,
                )
            elif "Script too short" in err_str or "too short" in err_str.lower():
                m2 = re.search(r"generated (\d+\.?\d*)s", err_str)
                actual_s = float(m2.group(1)) if m2 else target_duration * 0.5
                prompt = REPAIR_PROMPT_TOO_SHORT.format(
                    actual=actual_s,
                    target=target_duration,
                )
            elif "Invalid JSON" in err_str or "Expecting value" in err_str or not response.strip().startswith("{"):
                clean_t = re.sub(r"(?i)\s+in\s+\d+\s*(?:s|sec|secs|seconds?|min|mins|minutes?)\s*\??\s*$", "", topic.strip())
                prompt = (
                    f"Create an engaging explainer video script on the topic: {clean_t}. "
                    f"Target video length: {target_duration} seconds.\n"
                    f"CRITICAL: Output ONLY a single raw JSON object matching the schema. "
                    f"Do NOT write any thinking process, reasoning steps, or conversational preamble. "
                    f"Your response MUST start with '{{' and end with '}}'."
                )
            else:
                prompt = REPAIR_PROMPT.format(error=last_error)

        logger.info("Generating scene script attempt %d/%d", attempt + 1, max_retries)
        try:
            response = llm_complete(
                prompt=prompt,
                system=system_prompt,
                base_url=cfg.get("base_url"),
                model=cfg.get("model"),
                api_key=cfg.get("api_key"),
                timeout=cfg.get("timeout"),
            )
            emit("llm_response", attempt=attempt + 1, length=len(response))
        except LLMError as exc:
            last_error = exc
            logger.warning("LLM call failed on attempt %d/%d: %s", attempt + 1, max_retries, exc)
            emit("plan_rejected", attempt=attempt + 1, error=str(exc))
            if attempt < max_retries - 1:
                is_test_env = "fake" in str(cfg.get("base_url", "")) or "test" in str(cfg.get("base_url", ""))
                if not is_test_env:
                    time.sleep(2.0)
                continue
            raise

        try:
            fixed_response = _pre_heal_llm_json(response, target_duration=target_duration)
            script = validate_script(fixed_response)
            actual = script.total_duration
            if target_duration > 15 and len(script.scenes) >= 3 and actual < target_duration * 0.55:
                short_err = (
                    f"Script too short: generated {actual}s across {len(script.scenes)} scenes, "
                    f"target is {target_duration}s. Please generate more scenes to reach {target_duration}s."
                )
                last_error = Exception(short_err)
                emit("plan_rejected", attempt=attempt + 1, error=short_err)
                logger.warning("Script too short on attempt %d: %gs vs target %gs", attempt + 1, actual, target_duration)
                continue
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


def _assert_model_available(base_url: str, model: str, headers: dict) -> None:
    """Raise LLMError if model is not in Ollama /models list."""
    if "localhost" not in base_url and "127.0.0.1" not in base_url:
        return  # skip for cloud endpoints
    models_url = base_url.rstrip("/") + "/models"
    try:
        resp = requests.get(models_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            names = {m.get("id", "") for m in data.get("data", [])}
            if names and model not in names:
                raise LLMError(
                    f"Model '{model}' is not available in Ollama. "
                    f"Available: {sorted(names)}. "
                    f"Run: ollama pull {model}"
                )
    except LLMError:
        raise
    except Exception:
        pass


def test_llm_connection(base_url: str, model: str, api_key: str = "") -> dict[str, Any]:
    """Test connectivity to an OpenAI-compatible LLM endpoint."""
    if not base_url or not model:
        return {"ok": False, "error": "base_url and model are required"}

    if "generativelanguage.googleapis.com" in base_url and not base_url.rstrip("/").endswith("/openai"):
        base_url = base_url.rstrip("/") + "/openai"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Fast probe: GET /models — checks endpoint is up AND the model is available
    models_url = base_url.rstrip("/") + "/models"
    t0 = time.perf_counter()
    try:
        resp = requests.get(models_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            data = resp.json()
            names = {m.get("id", "") for m in data.get("data", [])}
            is_local = "localhost" in base_url or "127.0.0.1" in base_url
            if is_local and names and model not in names:
                return {
                    "ok": False,
                    "error": (
                        f"Model '{model}' not found in Ollama. "
                        f"Available: {sorted(names)}. "
                        f"Fix: update LLM_MODEL in .env or run `ollama pull {model}`"
                    ),
                    "available_models": sorted(names),
                }
            return {"ok": True, "model": model, "latency_ms": latency_ms}
        elif resp.status_code in (401, 403):
            return {"ok": False, "error": f"Authentication failed ({resp.status_code}): Invalid or missing API key."}
    except Exception:
        pass

    # Fallback probe: try chat endpoint with configurable timeout for cold-start models
    if ":11434" in base_url:
        chat_url = base_url.split("/v1")[0].rstrip("/") + "/api/chat"
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "think": False,
            "stream": False,
        }
    else:
        chat_url = base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
            "stream": False,
        }
    timeout_sec = int(os.environ.get("LLM_TIMEOUT", 120))
    t0 = time.perf_counter()
    try:
        resp = requests.post(chat_url, json=body, headers=headers, timeout=timeout_sec)
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
    "_build_system_prompt",
    "llm_complete",
    "llm_complete_timed",
    "generate_scene_script",
    "test_llm_connection",
]
