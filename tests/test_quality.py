"""Tests for snapreel/quality.py per AGENT_LOOP.md."""

import json
import pytest
from snapreel.quality import quality_pass
from snapreel.schema import SceneScript, Scene


def _mock_script():
    return SceneScript(
        title="Original Script",
        total_duration=5.0,
        scenes=[
            Scene(
                id="s1",
                template="title",
                duration=5.0,
                narration="Original narration text.",
                data={"heading": "Original Heading"},
            )
        ],
    )


def test_quality_pass_success(mocker):
    orig = _mock_script()
    improved_json = json.dumps({
        "title": "Improved Script",
        "total_duration": 5.0,
        "scenes": [
            {
                "id": "s1",
                "template": "title",
                "duration": 5.0,
                "narration": "Polished concise narration.",
                "data": {"heading": "Improved Heading"},
            }
        ],
    })

    mock_llm = mocker.patch("snapreel.quality.llm_complete", return_value=improved_json)
    events = []

    res = quality_pass(orig, on_event=events.append)
    assert res.title == "Improved Script"
    assert res.scenes[0].narration == "Polished concise narration."
    assert mock_llm.call_count == 1

    event_types = [e["type"] for e in events]
    assert "quality_start" in event_types
    assert "quality_accepted" in event_types


def test_quality_pass_invalid_llm_output_falls_back(mocker):
    orig = _mock_script()
    mock_llm = mocker.patch("snapreel.quality.llm_complete", return_value="Invalid JSON response")
    events = []

    res = quality_pass(orig, on_event=events.append)
    assert res.title == "Original Script"
    assert mock_llm.call_count == 1

    event_types = [e["type"] for e in events]
    assert "quality_start" in event_types
    assert "quality_rejected" in event_types


def test_quality_pass_disabled(mocker):
    orig = _mock_script()
    mock_llm = mocker.patch("snapreel.quality.llm_complete")
    events = []

    res = quality_pass(orig, on_event=events.append, enabled=False)
    assert res == orig
    assert mock_llm.call_count == 0
    assert any(e["type"] == "quality_skipped" for e in events)


def test_quality_pass_timeout_skip(mocker):
    orig = _mock_script()
    mock_llm = mocker.patch("snapreel.quality.llm_complete")
    events = []

    res = quality_pass(orig, on_event=events.append, prev_duration=25.0)
    assert res == orig
    assert mock_llm.call_count == 0
    assert any(e["type"] == "quality_skipped" for e in events)
