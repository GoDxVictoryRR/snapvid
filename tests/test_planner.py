"""Tests for snapreel/planner.py per TESTING.md specifications."""

import pytest
from snapreel.planner import build_prompt, generate
from snapreel.schema import SceneScript


def test_1_build_prompt_returns_non_empty_containing_topic():
    """Case 1: build_prompt('photosynthesis') returns a non-empty string containing 'photosynthesis'."""
    prompt = build_prompt("photosynthesis")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "photosynthesis" in prompt


def test_2_build_prompt_empty_raises_value_error():
    """Case 2: build_prompt('') raises ValueError."""
    with pytest.raises(ValueError):
        build_prompt("")

    with pytest.raises(ValueError):
        build_prompt("   ")


def test_3_generate_calls_generate_scene_script(mocker):
    """Verify generate(topic) delegates to generate_scene_script."""
    mock_script = SceneScript(
        title="Photosynthesis",
        total_duration=3.0,
        scenes=[
            {
                "id": "s1",
                "template": "title",
                "duration": 3.0,
                "narration": "Intro",
                "data": {"heading": "Photosynthesis"},
            }
        ],
    )
    mock_gen = mocker.patch("snapreel.planner.generate_scene_script", return_value=mock_script)

    result = generate("Photosynthesis")
    assert result == mock_script
    mock_gen.assert_called_once()
    assert "Photosynthesis" in mock_gen.call_args[0][0]
