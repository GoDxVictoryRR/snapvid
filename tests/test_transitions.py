"""Tests for snapreel/transitions.py per TRANSITIONS.md specifications."""

import pytest
from PIL import Image
from snapreel.transitions import (
    TRANSITION_FRAMES,
    blend_frames,
    generate_transition,
)


def test_blend_frames_fade():
    im_a = Image.new("RGB", (100, 100), (255, 0, 0))
    im_b = Image.new("RGB", (100, 100), (0, 0, 255))
    mid = blend_frames(im_a, im_b, 0.5, mode="fade")
    assert mid.size == (100, 100)
    pixel = mid.getpixel((50, 50))
    # Red should be ~127, Blue ~127
    assert isinstance(pixel, tuple)
    assert 120 <= pixel[0] <= 135
    assert pixel[1] == 0
    assert 120 <= pixel[2] <= 135


def test_blend_frames_modes():
    im_a = Image.new("RGB", (100, 100), (255, 0, 0))
    im_b = Image.new("RGB", (100, 100), (0, 255, 0))
    for mode in ["fade", "cross_dissolve", "slide_left", "slide_right", "zoom_in", "none"]:
        res = blend_frames(im_a, im_b, 0.5, mode=mode)
        assert isinstance(res, Image.Image)
        assert res.size == (100, 100)


def test_generate_transition_frame_count():
    im_a = Image.new("RGB", (100, 100), (255, 0, 0))
    im_b = Image.new("RGB", (100, 100), (0, 255, 0))
    frames = list(generate_transition(im_a, im_b, mode="slide_left", n_frames=TRANSITION_FRAMES))
    assert len(frames) == TRANSITION_FRAMES
    assert all(f.size == (100, 100) for f in frames)
