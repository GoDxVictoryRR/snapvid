"""Tests for snapreel/llm.py per TESTING.md specifications."""

import json
import os
import pytest
import requests

from snapreel.llm import LLMError, generate_scene_script, llm_complete, llm_complete_timed
from snapreel.schema import SceneScript

# Setup environment variables per TESTING.md
os.environ["LLM_BASE_URL"] = "http://fake/v1"
os.environ["LLM_MODEL"] = "fake-model"
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_TIMEOUT"] = "30"


@pytest.fixture(autouse=True)
def ensure_env():
    """Ensure test environment variables are active for every test."""
    os.environ["LLM_BASE_URL"] = "http://fake/v1"
    os.environ["LLM_MODEL"] = "fake-model"
    os.environ["LLM_API_KEY"] = ""
    os.environ["LLM_TIMEOUT"] = "30"


def _sample_valid_script_json() -> str:
    """Helper to return a valid JSON string matching SceneScript schema."""
    return json.dumps({
        "title": "Quantum Computing 101",
        "total_duration": 6.0,
        "scenes": [
            {
                "id": "scene-01",
                "template": "title",
                "duration": 3.0,
                "narration": "Introduction to qubits.",
                "data": {
                    "heading": "Quantum Computing",
                    "subheading": "Beyond Classical Limits",
                },
            },
            {
                "id": "scene-02",
                "template": "bullets",
                "duration": 3.0,
                "narration": "Core properties of qubits.",
                "data": {
                    "heading": "Principles",
                    "items": ["Superposition", "Entanglement"],
                },
            },
        ],
    })


def test_1_llm_complete_success(mocker):
    """Case 1: Mock requests.post returns valid JSON response -> llm_complete returns content string."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Simulated LLM response message",
                }
            }
        ]
    }
    mock_post = mocker.patch("requests.post", return_value=mock_response)

    output = llm_complete(prompt="Explain gravity", system="You are a helpful tutor")
    assert output == "Simulated LLM response message"

    # Verify requests.post call arguments
    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == "http://fake/v1/chat/completions"
    assert call_kwargs["json"]["model"] == "fake-model"
    assert call_kwargs["json"]["messages"] == [
        {"role": "system", "content": "You are a helpful tutor"},
        {"role": "user", "content": "Explain gravity"},
    ]


def test_2_llm_complete_http_500_raises_llmerror(mocker):
    """Case 2: Mock returns HTTP 500 -> llm_complete raises LLMError."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        "500 Server Error: Internal Server Error"
    )
    mocker.patch("requests.post", return_value=mock_response)

    with pytest.raises(LLMError) as exc_info:
        llm_complete(prompt="Explain black holes")

    assert "500" in str(exc_info.value) or "HTTP request failed" in str(exc_info.value)


def test_3_generate_scene_script_first_call_valid_zero_retries(mocker):
    """Case 3: generate_scene_script: first call returns valid scene JSON -> SceneScript returned, 0 retries."""
    valid_json = _sample_valid_script_json()
    mock_llm = mocker.patch("snapreel.llm.llm_complete", return_value=valid_json)

    script = generate_scene_script("Quantum Computing")
    assert isinstance(script, SceneScript)
    assert script.title == "Quantum Computing 101"
    assert len(script.scenes) == 2
    assert mock_llm.call_count == 1


def test_4_generate_scene_script_repair_after_one_retry(mocker):
    """Case 4: generate_scene_script: first call returns invalid JSON, second call returns valid -> SceneScript returned after 1 retry."""
    invalid_json = '{"title": "Broken Script", "scenes": []}'  # Fails 0 scenes validation
    valid_json = _sample_valid_script_json()

    mock_llm = mocker.patch(
        "snapreel.llm.llm_complete",
        side_effect=[invalid_json, valid_json],
    )

    script = generate_scene_script("Quantum Computing")
    assert isinstance(script, SceneScript)
    assert script.title == "Quantum Computing 101"
    assert mock_llm.call_count == 2


def test_5_generate_scene_script_all_invalid_raises_llmerror(mocker):
    """Case 5: generate_scene_script: all 3 calls return invalid JSON -> raises LLMError after 3 retries."""
    mock_llm = mocker.patch(
        "snapreel.llm.llm_complete",
        side_effect=[
            '{"invalid_json": 1}',
            '{"invalid_json": 2}',
            '{"invalid_json": 3}',
        ],
    )

    with pytest.raises(LLMError) as exc_info:
        generate_scene_script("Impossible Topic")

    assert mock_llm.call_count == 3
    assert "retries" in str(exc_info.value).lower()


def test_6_generate_scene_script_emits_events(mocker):
    """Case 6: generate_scene_script emits planning_start, llm_response, and plan_accepted events."""
    valid_json = _sample_valid_script_json()
    mocker.patch("snapreel.llm.llm_complete", return_value=valid_json)
    events = []

    script = generate_scene_script("Gravity", on_event=events.append)
    assert script.title == "Quantum Computing 101"
    types = [e["type"] for e in events]
    assert "planning_start" in types
    assert "llm_response" in types
    assert "plan_accepted" in types


def test_7_llm_complete_timed(mocker):
    """Case 7: llm_complete_timed returns content and metrics dictionary."""
    mocker.patch("snapreel.llm.llm_complete", return_value="Here is five words.")
    content, metrics = llm_complete_timed("Hello")
    assert content == "Here is five words."
    assert "tokens" in metrics
    assert "seconds" in metrics
    assert metrics["tokens"] == 4
