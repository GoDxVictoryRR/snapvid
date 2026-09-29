"""Tests for snapreel/schema.py per TESTING.md specifications."""

import json
import pytest
from pydantic import ValidationError

from snapreel.schema import SceneScript, validate_script


def _create_base_script(scenes: list[dict], total_duration: float = 3.0, title: str = "Test Video") -> dict:
    """Helper to assemble a valid script dictionary."""
    return {
        "title": title,
        "total_duration": total_duration,
        "scenes": scenes,
    }


def test_1_valid_script_with_all_six_templates():
    """Case 1: Valid script with all 6 templates -> returns SceneScript, no error."""
    raw_dict = {
        "title": "Comprehensive Test",
        "total_duration": 21.0,
        "scenes": [
            {
                "id": "scene-01",
                "template": "title",
                "duration": 3.0,
                "narration": "Welcome to the full template demonstration.",
                "data": {
                    "heading": "SnapReel Overview",
                    "subheading": "Offline AI Video Maker",
                },
            },
            {
                "id": "scene-02",
                "template": "bullets",
                "duration": 4.0,
                "narration": "Here are key highlights.",
                "data": {
                    "heading": "Core Features",
                    "items": ["Offline execution", "Fast rendering", "Zero cloud lock-in"],
                },
            },
            {
                "id": "scene-03",
                "template": "bar_chart",
                "duration": 3.5,
                "narration": "Observe the performance metrics.",
                "data": {
                    "heading": "Speed Benchmark",
                    "labels": ["Ollama", "GenieX", "Cloud"],
                    "values": [12.5, 4.2, 8.1],
                    "unit": "s",
                },
            },
            {
                "id": "scene-04",
                "template": "counter",
                "duration": 3.5,
                "narration": "Watch the counter scale upwards.",
                "data": {
                    "label": "Frames Rendered",
                    "from": 0,
                    "to": 900,
                    "unit": "fps",
                },
            },
            {
                "id": "scene-05",
                "template": "code_block",
                "duration": 4.0,
                "narration": "Simple code snippet powering the video.",
                "data": {
                    "heading": "Python Hook",
                    "language": "python",
                    "code": "import snapreel\nscript = snapreel.plan('Topic')",
                },
            },
            {
                "id": "scene-06",
                "template": "kinetic",
                "duration": 3.0,
                "narration": "Final punchy kinetic message.",
                "data": {
                    "lines": ["Create", "Iterate", "Inspire"],
                },
            },
        ],
    }

    result = validate_script(json.dumps(raw_dict))
    assert isinstance(result, SceneScript)
    assert len(result.scenes) == 6
    assert result.total_duration == 21.0
    assert result.scenes[0].template == "title"
    assert result.scenes[3].data["from"] == 0


def test_2_title_template_subheading_omitted():
    """Case 2: title template with subheading omitted -> valid (optional field)."""
    raw_dict = _create_base_script(
        scenes=[
            {
                "id": "scene-01",
                "template": "title",
                "duration": 3.0,
                "narration": "Title without subheading.",
                "data": {
                    "heading": "Solo Title Card",
                },
            }
        ],
        total_duration=3.0,
    )

    result = validate_script(json.dumps(raw_dict))
    assert isinstance(result, SceneScript)
    assert result.scenes[0].data.heading == "Solo Title Card"
    assert result.scenes[0].data.subheading is None


def test_3_bar_chart_with_two_items():
    """Case 3: bar_chart with 2 items -> valid."""
    raw_dict = _create_base_script(
        scenes=[
            {
                "id": "scene-01",
                "template": "bar_chart",
                "duration": 3.0,
                "narration": "Two-item bar chart.",
                "data": {
                    "heading": "Option A vs B",
                    "labels": ["Option A", "Option B"],
                    "values": [45, 90],
                    "unit": "%",
                },
            }
        ],
        total_duration=3.0,
    )

    result = validate_script(json.dumps(raw_dict))
    assert isinstance(result, SceneScript)
    assert len(result.scenes[0].data.labels) == 2
    assert len(result.scenes[0].data.values) == 2


def test_4_bar_chart_with_nine_items_raises_validation_error():
    """Case 4: bar_chart with 9 items -> raises ValidationError ("max 8")."""
    raw_dict = _create_base_script(
        scenes=[
            {
                "id": "scene-01",
                "template": "bar_chart",
                "duration": 3.0,
                "narration": "Nine items should exceed the maximum of 8.",
                "data": {
                    "heading": "Overloaded Bar Chart",
                    "labels": [f"Item {i}" for i in range(1, 10)],
                    "values": [float(i * 10) for i in range(1, 10)],
                },
            }
        ],
        total_duration=3.0,
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_script(json.dumps(raw_dict))

    assert "max 8" in str(exc_info.value).lower()


def test_5_unknown_template_name_raises_validation_error():
    """Case 5: Unknown template name -> ValidationError."""
    raw_dict = _create_base_script(
        scenes=[
            {
                "id": "scene-01",
                "template": "unknown_future_template",
                "duration": 3.0,
                "narration": "This should fail because template is unrecognized.",
                "data": {
                    "heading": "Invalid",
                },
            }
        ],
        total_duration=3.0,
    )

    with pytest.raises(ValidationError):
        validate_script(json.dumps(raw_dict))


def test_6_duration_below_min_raises_validation_error():
    """Case 6: duration = 1 (below min 2) -> ValidationError."""
    raw_dict = _create_base_script(
        scenes=[
            {
                "id": "scene-01",
                "template": "title",
                "duration": 1.0,
                "narration": "Duration is too brief.",
                "data": {
                    "heading": "Too Fast",
                },
            }
        ],
        total_duration=1.0,
    )

    with pytest.raises(ValidationError):
        validate_script(json.dumps(raw_dict))


def test_7_narration_over_200_chars_raises_validation_error():
    """Case 7: narration > 200 chars -> ValidationError."""
    long_narration = "A" * 201
    raw_dict = _create_base_script(
        scenes=[
            {
                "id": "scene-01",
                "template": "title",
                "duration": 4.0,
                "narration": long_narration,
                "data": {
                    "heading": "Excessive Narration",
                },
            }
        ],
        total_duration=4.0,
    )

    with pytest.raises(ValidationError):
        validate_script(json.dumps(raw_dict))


def test_8_total_duration_mismatch_raises_validation_error():
    """Case 8: total_duration mismatch > 0.1 -> ValidationError."""
    raw_dict = _create_base_script(
        scenes=[
            {
                "id": "scene-01",
                "template": "title",
                "duration": 5.0,
                "narration": "Checking duration mismatch.",
                "data": {
                    "heading": "Mismatch Check",
                },
            }
        ],
        total_duration=5.5,  # 0.5 mismatch > 0.1 tolerance
    )

    with pytest.raises(ValidationError):
        validate_script(json.dumps(raw_dict))


def test_9_zero_scenes_raises_validation_error():
    """Case 9: 0 scenes -> ValidationError."""
    raw_dict = {
        "title": "Empty Video",
        "total_duration": 0.0,
        "scenes": [],
    }

    with pytest.raises(ValidationError):
        validate_script(json.dumps(raw_dict))


def test_10_twenty_one_scenes_raises_validation_error():
    """Case 10: 21 scenes (over max 20) -> ValidationError."""
    scenes = [
        {
            "id": f"scene-{i:02d}",
            "template": "title",
            "duration": 2.0,
            "narration": f"Scene number {i}",
            "data": {"heading": f"Title {i}"},
        }
        for i in range(1, 22)
    ]
    raw_dict = {
        "title": "Too Many Scenes Video",
        "total_duration": 42.0,
        "scenes": scenes,
    }

    with pytest.raises(ValidationError):
        validate_script(json.dumps(raw_dict))


def test_11_malformed_json_string_raises_validation_error():
    """Case 11: Malformed JSON string -> ValidationError (json.JSONDecodeError wrapped)."""
    malformed_json = '{"title": "Unclosed Object", "scenes": ['

    with pytest.raises(ValidationError) as exc_info:
        validate_script(malformed_json)

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)
