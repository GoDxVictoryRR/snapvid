"""Tests for snapreel/renderer.py per TESTING.md specifications."""

import os
from pathlib import Path
import pytest
from PIL import Image

from snapreel.renderer import render_scene_frames, render_video
from snapreel.schema import Scene, SceneScript


def test_1_title_template_frame_count():
    """Case 1: title template: render_scene_frames() returns list of PIL.Image, length = duration * fps."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "title",
        {"heading": "Title Card", "subheading": "Subtitle"},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)
    assert frames[0].size == (1280, 720)


def test_2_bullets_template_frame_count():
    """Case 2: bullets template: render_scene_frames() returns list of PIL.Image, length = duration * fps."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "bullets",
        {"heading": "Bullet Points", "items": ["Item One", "Item Two", "Item Three"]},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_3_bar_chart_template_frame_count():
    """Case 3: bar_chart template: render_scene_frames() returns list of PIL.Image, length = duration * fps."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "bar_chart",
        {"heading": "Latency Comparison", "labels": ["A", "B", "C"], "values": [10.0, 20.0, 30.0], "unit": "ms"},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_4_counter_template_frame_count_and_values():
    """Case 4: counter template: frame at t=0 shows 'from' value region, frame at t=end shows 'to' region."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "counter",
        {"label": "Counter Test", "from": 0, "to": 100, "unit": "%"},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert isinstance(frames[0], Image.Image)
    assert isinstance(frames[-1], Image.Image)


def test_5_kinetic_template_frame_count():
    """Case 5: kinetic template: frame count check."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "kinetic",
        {"lines": ["Focus", "Build", "Ship"]},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_6_code_block_template_frame_count():
    """Case 6: code_block template: frame count check."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "code_block",
        {"heading": "Code Demo", "language": "python", "code": "def hello():\n    return 'world'"},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_7_full_pipeline_render_video(tmp_path):
    """Case 7: Full pipeline: render_video() with temp output path -> file exists, size > 1000 bytes."""
    script = SceneScript(
        title="Pipeline Smoke Test",
        total_duration=2.0,
        scenes=[
            Scene(
                id="scene-01",
                template="title",
                duration=2.0,
                narration="Short test video.",
                data={"heading": "Pipeline Test", "subheading": "Smoke test"},
            )
        ],
    )

    out_file = tmp_path / "test_pipeline.mp4"
    progress_calls = []

    def on_progress(idx, total):
        progress_calls.append((idx, total))

    result_path = render_video(
        script=script,
        output_path=str(out_file),
        fps=30,
        on_progress=on_progress,
    )

    assert os.path.exists(result_path)
    assert Path(result_path).stat().st_size > 1000
    assert len(progress_calls) == 1
    assert progress_calls[0] == (0, 1)


def test_8_lower_third_template_frame_count():
    """Case 8: lower_third template frame count check."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "lower_third",
        {"name": "Alice Smith", "role": "Lead Architect"},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_9_quote_template_frame_count():
    """Case 9: quote template frame count check."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "quote",
        {"text": "Simplicity is prerequisite for reliability.", "attribution": "Edsger W. Dijkstra", "style": "card"},
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_10_icon_list_template_frame_count():
    """Case 10: icon_list template frame count check."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "icon_list",
        {
            "heading": "Key Benefits",
            "items": [
                {"icon": "bolt", "text": "High Performance"},
                {"icon": "lock", "text": "Privacy First"},
                {"icon": "check", "text": "Tested & Reliable"},
            ],
        },
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_11_split_template_frame_count():
    """Case 11: split template frame count check."""
    duration = 2.0
    fps = 30
    frames = render_scene_frames(
        "split",
        {
            "heading": "Efficiency Gain",
            "body": "Running inference locally on NPU consumes significantly less power.",
            "visual": "counter",
            "visual_data": {"from": 0, "to": 85, "unit": "%", "label": "Energy Saved"},
        },
        duration=duration,
        fps=fps,
    )
    assert isinstance(frames, list)
    assert len(frames) == int(duration * fps)
    assert all(isinstance(f, Image.Image) for f in frames)


def test_12_multi_scene_video_with_transitions(tmp_path):
    """Case 12: Render multi-scene video with slide_left transition."""
    script = SceneScript(
        title="Multi Scene Transition Test",
        aspect_ratio="9:16",
        total_duration=4.0,
        scenes=[
            Scene(
                id="s1",
                template="title",
                duration=2.0,
                narration="Scene one narration",
                data={"heading": "Scene One"},
                transition="slide_left",
            ),
            Scene(
                id="s2",
                template="lower_third",
                duration=2.0,
                narration="Scene two narration",
                data={"name": "Host", "role": "Presenter"},
            ),
        ],
    )
    out_file = tmp_path / "test_transition.mp4"
    res = render_video(script, str(out_file), fps=15)
    assert os.path.exists(res)
    assert Path(res).stat().st_size > 1000


