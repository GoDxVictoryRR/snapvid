"""Tests for snapreel/tts.py per TESTING.md and VOICE.md specifications."""

import os
from pathlib import Path
import wave
import pytest

from snapreel.schema import Scene
from snapreel.tts import (
    build_captions,
    narrate,
    _narrate_kokoro,
    _narrate_edge,
    _narrate_sapi,
)


def test_1_narrate_non_windows_raises_runtime_error(mocker):
    """Case 1: On non-Windows with SAPI engine -> raises RuntimeError."""
    mocker.patch("platform.system", return_value="Linux")
    with pytest.raises(RuntimeError, match="TTS only supported on Windows"):
        narrate("Testing non-windows check", "output/dummy.wav", engine="sapi")


def test_2_narrate_windows_with_mocked_win32com(mocker, tmp_path):
    """Case 2: On Windows with win32com mocked -> output file created."""
    mocker.patch("platform.system", return_value="Windows")
    out_wav = tmp_path / "mock_speech.wav"

    mock_speaker = mocker.MagicMock()
    mock_stream = mocker.MagicMock()

    def mock_close():
        with wave.open(str(out_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 16000)

    mock_stream.Close.side_effect = mock_close

    def mock_dispatch(clsid):
        if "Voice" in clsid:
            return mock_speaker
        return mock_stream

    mocker.patch("win32com.client.Dispatch", side_effect=mock_dispatch)

    duration = narrate("Synthesize test narration", str(out_wav), engine="sapi")
    assert out_wav.exists()
    assert duration == pytest.approx(1.0, rel=1e-2)
    mock_speaker.Speak.assert_called_once_with("Synthesize test narration")


def test_3_build_captions_cumulative_timing():
    """Case 3: build_captions with 3 scenes, durations [5.0, 3.0, 7.0] -> returns list of 3 dicts with correct cumulative start/end times."""
    scenes = [
        Scene(id="scene-01", template="title", duration=5.0, narration="First scene narration.", data={"heading": "S1"}),
        Scene(id="scene-02", template="bullets", duration=3.0, narration="Second scene narration.", data={"heading": "S2", "items": ["Item A"]}),
        Scene(id="scene-03", template="counter", duration=7.0, narration="Third scene narration.", data={"label": "S3", "from": 0, "to": 100}),
    ]
    durations = [5.0, 3.0, 7.0]

    captions = build_captions(scenes, durations)

    assert len(captions) == 3
    assert captions[0] == {
        "scene_id": "scene-01",
        "start_sec": 0.0,
        "end_sec": 5.0,
        "text": "First scene narration.",
    }
    assert captions[1] == {
        "scene_id": "scene-02",
        "start_sec": 5.0,
        "end_sec": 8.0,
        "text": "Second scene narration.",
    }
    assert captions[2] == {
        "scene_id": "scene-03",
        "start_sec": 8.0,
        "end_sec": 15.0,
        "text": "Third scene narration.",
    }


def test_4_kokoro_succeeds_called_with_default_voice(mocker):
    """VOICE.md Case 1: kokoro import succeeds -> _narrate_kokoro called with default voice."""
    mock_kokoro = mocker.patch("snapreel.tts._narrate_kokoro", return_value=3.5)
    dur = narrate("Test kokoro narration", "dummy.wav", engine="auto")
    assert dur == 3.5
    mock_kokoro.assert_called_once_with("Test kokoro narration", "dummy.wav", voice="af_heart")


def test_5_kokoro_fails_falls_through_to_edge(mocker):
    """VOICE.md Case 2: kokoro import fails -> falls through to edge."""
    mocker.patch("snapreel.tts._narrate_kokoro", side_effect=ImportError("No module named 'kokoro'"))
    mock_edge = mocker.patch("snapreel.tts._narrate_edge", return_value=2.8)
    dur = narrate("Test edge narration", "dummy.wav", engine="auto")
    assert dur == 2.8
    mock_edge.assert_called_once_with("Test edge narration", "dummy.wav", voice="en-US-AriaNeural")


def test_6_edge_and_kokoro_fail_falls_through_to_sapi(mocker):
    """VOICE.md Case 3: edge + kokoro fail -> falls through to sapi."""
    mocker.patch("snapreel.tts._narrate_kokoro", side_effect=ImportError("No kokoro"))
    mocker.patch("snapreel.tts._narrate_edge", side_effect=RuntimeError("Edge network timeout"))
    mock_sapi = mocker.patch("snapreel.tts._narrate_sapi", return_value=4.0)
    dur = narrate("Test sapi fallback", "dummy.wav", engine="auto")
    assert dur == 4.0
    mock_sapi.assert_called_once_with("Test sapi fallback", "dummy.wav")


def test_7_engine_sapi_explicitly_skips_others(mocker):
    """VOICE.md Case 4: engine='sapi' explicitly -> skips kokoro/edge regardless."""
    mock_kokoro = mocker.patch("snapreel.tts._narrate_kokoro", return_value=3.0)
    mock_edge = mocker.patch("snapreel.tts._narrate_edge", return_value=3.0)
    mock_sapi = mocker.patch("snapreel.tts._narrate_sapi", return_value=4.2)
    dur = narrate("Test explicit sapi", "dummy.wav", engine="sapi")
    assert dur == 4.2
    mock_kokoro.assert_not_called()
    mock_edge.assert_not_called()
    mock_sapi.assert_called_once_with("Test explicit sapi", "dummy.wav")
