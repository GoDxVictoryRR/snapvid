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


def test_8_reconcile_durations():
    """CAPTIONS.md: reconcile_durations expands scenes when audio is longer."""
    from snapreel.schema import Scene, SceneScript
    from snapreel.tts import reconcile_durations

    script = SceneScript(
        title="Reconcile Test",
        total_duration=6.0,
        scenes=[
            Scene(id="s1", template="title", duration=3.0, narration="Short", data={"heading": "S1"}),
            Scene(id="s2", template="title", duration=3.0, narration="Long", data={"heading": "S2"}),
        ],
    )
    # Audio durations: s1 is 2.0s (< 3.0s), s2 is 4.0s (> 3.0s)
    reconciled = reconcile_durations(script, [2.0, 4.0])
    assert reconciled.scenes[0].duration == 3.0
    assert reconciled.scenes[1].duration == 4.3  # 4.0 + 0.3 padding
    assert reconciled.total_duration == 7.3


def test_9_concat_audio(tmp_path):
    """CAPTIONS.md: concat_audio writes a valid multi-scene audio wav."""
    import wave
    from snapreel.tts import concat_audio

    # Create two 1-second sine wave or silent test WAVs
    f1 = tmp_path / "s1.wav"
    f2 = tmp_path / "s2.wav"
    out_wav = tmp_path / "combined.wav"

    sample_rate = 22050
    for p in (f1, f2):
        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00" * (sample_rate * 2))  # 1 sec

    res = concat_audio([str(f1), str(f2)], [1.5, 1.5], str(out_wav), sample_rate=sample_rate)
    assert os.path.exists(res)
    with wave.open(res, "rb") as wf:
        total_sec = wf.getnframes() / float(wf.getframerate())
        assert abs(total_sec - 3.0) < 0.1


def test_10_prepare_audio(tmp_path, mocker):
    """CAPTIONS.md: prepare_audio synthesizes audio per scene."""
    from snapreel.schema import Scene, SceneScript
    from snapreel.tts import prepare_audio

    mocker.patch("snapreel.tts.narrate", return_value=2.5)
    script = SceneScript(
        title="Prep Test",
        total_duration=5.0,
        scenes=[
            Scene(id="sc1", template="title", duration=2.5, narration="Hello world", data={"heading": "H1"}),
            Scene(id="sc2", template="title", duration=2.5, narration="", data={"heading": "H2"}),
        ],
    )
    paths, durations = prepare_audio(script, str(tmp_path))
    assert len(paths) == 2
    assert durations[0] == 2.5
    assert durations[1] == 0.0


def test_11_draw_caption_overlay():
    """CAPTIONS.md: draw_caption_overlay renders subtitle text."""
    from PIL import Image
    from snapreel.tts import draw_caption_overlay

    canvas = Image.new("RGBA", (1280, 720), (20, 20, 30, 255))
    draw_caption_overlay(canvas, "This is a live test caption overlay.", style="pill")
    assert isinstance(canvas, Image.Image)


def test_12_reconcile_durations_format_30s():
    """Verify 30s format reconciles to exactly 30.0s."""
    from snapreel.schema import Scene, SceneScript
    from snapreel.tts import reconcile_durations

    scenes = [
        Scene(id=f"s{i}", template="title", duration=7.5, narration=f"Scene {i}", data={"heading": f"H{i}"})
        for i in range(4)
    ]
    script = SceneScript(title="30s Video", total_duration=30.0, scenes=scenes)
    # Audio durations total 24.0s
    audio_durations = [6.0, 5.5, 6.5, 6.0]
    reconciled = reconcile_durations(script, audio_durations, min_tail_padding=0.5, target_duration=30.0)
    assert reconciled.total_duration == 30.0
    for i, s in enumerate(reconciled.scenes):
        assert s.duration >= audio_durations[i] + 0.5


def test_13_reconcile_durations_format_60s():
    """Verify 60s format reconciles to exactly 60.0s."""
    from snapreel.schema import Scene, SceneScript
    from snapreel.tts import reconcile_durations

    scenes = [
        Scene(id=f"s{i}", template="bullets", duration=10.0, narration=f"Scene {i}", data={"heading": f"H{i}", "items": ["Pt 1"]})
        for i in range(6)
    ]
    script = SceneScript(title="60s Video", total_duration=60.0, scenes=scenes)
    audio_durations = [8.5, 7.8, 9.0, 8.2, 8.9, 7.6]
    reconciled = reconcile_durations(script, audio_durations, min_tail_padding=0.6, target_duration=60.0)
    assert reconciled.total_duration == 60.0
    for i, s in enumerate(reconciled.scenes):
        assert s.duration >= audio_durations[i] + 0.6


def test_14_reconcile_durations_format_120s():
    """Verify 120s (2 min) format reconciles to exactly 120.0s."""
    from snapreel.schema import Scene, SceneScript
    from snapreel.tts import reconcile_durations

    scenes = [
        Scene(id=f"s{i}", template="title", duration=12.0, narration=f"Scene {i}", data={"heading": f"H{i}"})
        for i in range(10)
    ]
    script = SceneScript(title="2 Min Video", total_duration=120.0, scenes=scenes)
    audio_durations = [9.5] * 10  # 95s audio total
    reconciled = reconcile_durations(script, audio_durations, min_tail_padding=0.8, target_duration=120.0)
    assert reconciled.total_duration == 120.0


def test_15_reconcile_durations_format_300s_five_minute():
    """Verify 300s (5 min) format reconciles to exactly 300.0s (not 3.45 min / 207s)."""
    from snapreel.schema import Scene, SceneScript
    from snapreel.tts import reconcile_durations

    scenes = [
        Scene(id=f"s{i}", template="title", duration=15.0, narration=f"Detailed Scene {i}", data={"heading": f"Topic {i}"})
        for i in range(20)
    ]
    script = SceneScript(title="5 Min Deep Dive", total_duration=300.0, scenes=scenes)
    # Audio durations: ~11.5s per scene, total 230s (would previously cap at 230 + 20*1.4 = 258s or 3.45 min)
    audio_durations = [11.5] * 20
    reconciled = reconcile_durations(script, audio_durations, min_tail_padding=0.8, target_duration=300.0)
    assert reconciled.total_duration == 300.0
    assert sum(s.duration for s in reconciled.scenes) == pytest.approx(300.0, rel=1e-3)
    for i, s in enumerate(reconciled.scenes):
        assert s.duration >= audio_durations[i] + 0.8


