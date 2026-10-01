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


def test_7_narration_over_1200_chars_raises_validation_error():
    """Case 7: narration > 1200 chars -> ValidationError (limit raised to 1200 for long scenes)."""
    long_narration = "A" * 1201
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


def test_10_thirty_one_scenes_raises_validation_error():
    """Case 10: 31 scenes (over new max 30) -> ValidationError."""
    scenes = [
        {
            "id": f"scene-{i:02d}",
            "template": "title",
            "duration": 2.0,
            "narration": f"Scene number {i}",
            "data": {"heading": f"Title {i}"},
        }
        for i in range(1, 32)
    ]
    raw_dict = {
        "title": "Too Many Scenes Video",
        "total_duration": 62.0,
        "scenes": scenes,
    }

    with pytest.raises(ValidationError):
        validate_script(json.dumps(raw_dict))


def test_11_malformed_json_string_raises_validation_error():
    """Case 11: Severely malformed JSON -> ValidationError raised.

    The auto-repair in validate_script may be able to partially fix simple
    truncation (closing open brackets), but the result will still fail Pydantic
    validation (missing required fields). Either way a ValidationError is expected.
    """
    # This input is so broken that even after repair it fails Pydantic validation
    malformed_json = '{not valid json at all %%% :::'

    with pytest.raises(ValidationError):
        validate_script(malformed_json)


def test_12_valid_aspect_ratios_and_target_duration():
    """Case 12: Test custom aspect ratios and target duration."""
    for ratio in ["16:9", "9:16", "1:1", "4:3"]:
        raw = _create_base_script(
            scenes=[{
                "id": "scene-01",
                "template": "title",
                "duration": 3.0,
                "narration": "Aspect ratio test",
                "data": {"heading": "Testing Aspect Ratio"},
                "transition": "slide_left",
            }],
            total_duration=3.0,
        )
        raw["aspect_ratio"] = ratio
        raw["target_duration"] = 30
        res = validate_script(json.dumps(raw))
        assert res.aspect_ratio == ratio
        assert res.target_duration == 30
        assert res.scenes[0].transition == "slide_left"


def test_13_invalid_aspect_ratio_raises_validation_error():
    """Case 13: Invalid aspect ratio raises ValidationError."""
    raw = _create_base_script(
        scenes=[{
            "id": "scene-01",
            "template": "title",
            "duration": 3.0,
            "narration": "Invalid ratio",
            "data": {"heading": "Invalid Ratio"},
        }],
        total_duration=3.0,
    )
    raw["aspect_ratio"] = "21:9"
    with pytest.raises(ValidationError) as exc_info:
        validate_script(json.dumps(raw))
    assert "aspect_ratio must be one of" in str(exc_info.value)


def test_14_auto_repair_missing_comma_between_scenes():
    """Case 14: Missing comma between scene objects is auto-repaired by validate_script.

    This simulates the exact production error:
      'Expecting ','  delimiter: line 39 column 5'
    which occurs when the LLM omits the comma between two scene JSON objects.
    """
    # Two scene objects with NO comma between them — the exact LLM failure mode
    broken_json = """{
  "title": "Test Video",
  "total_duration": 7.0,
  "scenes": [
    {
      "id": "s1",
      "template": "title",
      "duration": 4.0,
      "narration": "Hello world",
      "data": {"heading": "Hello", "subheading": null}
    }
    {
      "id": "s2",
      "template": "kinetic",
      "duration": 3.0,
      "narration": "Goodbye world",
      "data": {"lines": ["Goodbye"]}
    }
  ]
}"""
    script = validate_script(broken_json)
    assert len(script.scenes) == 2
    assert script.total_duration == 7.0


def test_15_auto_repair_trailing_comma():
    """Case 15: Trailing comma before closing brace is auto-repaired."""
    broken_json = """{
  "title": "Test",
  "total_duration": 4.0,
  "scenes": [
    {
      "id": "s1",
      "template": "title",
      "duration": 4.0,
      "narration": "Hi",
      "data": {"heading": "Hi", "subheading": null},
    },
  ]
}"""
    script = validate_script(broken_json)
    assert script.title == "Test"


def test_16_auto_extract_json_with_thinking_preamble():
    """Case 16: LLM output with thinking process or conversational preamble is cleanly extracted."""
    # Test with thinking process followed by markdown code fence
    llm_output_fenced = """Here's a thinking process that leads to the suggested script:
1. Understand the goal: explain Transformer architecture simply.
2. Structure the scenes into intro, attention, and backpropagation.
3. Keep total duration to 6 seconds.

```json
{
  "title": "Transformer Architecture",
  "total_duration": 6.0,
  "scenes": [
    {
      "id": "s1",
      "template": "title",
      "duration": 3.0,
      "narration": "Transformers revolutionized natural language processing.",
      "data": {"heading": "Transformers", "subheading": "Attention is All You Need"}
    },
    {
      "id": "s2",
      "template": "kinetic",
      "duration": 3.0,
      "narration": "Self-attention processes tokens in parallel.",
      "data": {"lines": ["Self-Attention", "Parallel Compute"]}
    }
  ]
}
```
Hope this script helps!"""
    script1 = validate_script(llm_output_fenced)
    assert script1.title == "Transformer Architecture"
    assert len(script1.scenes) == 2

    # Test with thinking process followed by raw JSON (no fences)
    llm_output_raw = """Here's a thinking process that leads to the suggested script:
{
  "title": "Transformers Simply",
  "total_duration": 3.0,
  "scenes": [
    {
      "id": "s1",
      "template": "title",
      "duration": 3.0,
      "narration": "Transformers in three seconds.",
      "data": {"heading": "Transformers", "subheading": null}
    }
  ]
}"""
    script2 = validate_script(llm_output_raw)
    assert script2.title == "Transformers Simply"

    # Test with <think> tag
    llm_output_think = """<think>
Deep reasoning steps...
Evaluating scene durations...
</think>
{
  "title": "Think Tag Test",
  "total_duration": 3.0,
  "scenes": [
    {
      "id": "s1",
      "template": "title",
      "duration": 3.0,
      "narration": "Testing think tag stripping.",
      "data": {"heading": "Think Tag", "subheading": null}
    }
  ]
}"""
    script3 = validate_script(llm_output_think)
    assert script3.title == "Think Tag Test"


def test_17_thinking_process_with_embedded_braces_and_unclosed_fences():
    """Case 17: Thinking text containing non-JSON braces and unclosed code fence is correctly parsed."""
    # Text with non-JSON braces in notes, followed by an unclosed code block (truncated due to token limit)
    truncated_llm_output = """Here's a thinking process that leads to the suggested script:
1. Understand the goal:
   - Topic: Explain Transformer architecture, attention heads, and backpropagation simply.
   - We might consider components like {attention_heads, feed_forward, residual}.
   - Math notes: {Q, K, V} = softmax(QK^T / sqrt(d_k)) * V.
2. Outline scenes:
   - Scene 1: {heading: "Transformers"}
3. Draft the JSON:
```json
{
  "title": "Transformer Architecture Explained",
  "total_duration": 6.0,
  "scenes": [
    {
      "id": "s1",
      "template": "title",
      "duration": 3.0,
      "narration": "Welcome to Transformers.",
      "data": {"heading": "Transformers", "subheading": null}
    },
    {
      "id": "s2",
      "template": "kinetic",
      "duration": 3.0,
      "narration": "Self-attention processes tokens in parallel.",
      "data": {"lines": ["Self-Attention", "Parallel Compute"]}
    }
  ]
}
"""
    script = validate_script(truncated_llm_output)
    assert script.title == "Transformer Architecture Explained"
    assert len(script.scenes) == 2

    # Single-quoted keys and values
    single_quote_json = """{'title': 'Single Quote Test', 'total_duration': 3.0, 'scenes': [{'id': 's1', 'template': 'title', 'duration': 3.0, 'narration': 'Hi', 'data': {'heading': 'Hello', 'subheading': None}}]}"""
    script_sq = validate_script(single_quote_json)
    assert script_sq.title == "Single Quote Test"


