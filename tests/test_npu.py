"""Tests for snapreel/npu.py per NPU.md."""

import pytest
from snapreel.npu import NPUProfiler, get_latest_benchmark
from snapreel.schema import SceneScript, Scene


def _mock_script():
    return SceneScript(
        title="NPU Test",
        total_duration=5.0,
        scenes=[
            Scene(
                id="s1",
                template="title",
                duration=5.0,
                narration="Testing NPU profiling on Snapdragon.",
                data={"heading": "Test Heading"},
            )
        ],
    )


def test_is_snapdragon_device_detection(mocker):
    profiler = NPUProfiler()

    mocker.patch("platform.processor", return_value="Snapdragon X Elite")
    assert profiler.is_snapdragon_device() is True

    mocker.patch("platform.processor", return_value="Intel Core i7")
    mocker.patch("platform.machine", return_value="AMD64")
    mocker.patch.dict("os.environ", {"LLM_BASE_URL": "http://localhost:11434/v1"})
    assert profiler.is_snapdragon_device() is False

    # GenieX on port 8080 detection
    mocker.patch.dict("os.environ", {"LLM_BASE_URL": "http://localhost:8080/v1"})
    assert profiler.is_snapdragon_device() is True


def test_measure_llm_timing():
    profiler = NPUProfiler()

    def dummy_script_fn(topic: str):
        return _mock_script()

    timing = profiler.measure_llm("Quantum Computing", dummy_script_fn)
    assert "seconds" in timing
    assert timing["seconds"] >= 0
    assert timing["tokens"] > 0
    assert timing["tokens_per_sec"] > 0
    assert timing["scenes"] == 1
    assert profiler.last_measurement == timing


def test_to_readme_table():
    profiler = NPUProfiler()
    table = profiler.to_readme_table()
    assert "| Component" in table
    assert "Qwen3-4B" in table
    assert "Kokoro TTS" in table
    assert "Pillow renderer" in table


def test_get_latest_benchmark():
    data = get_latest_benchmark()
    assert isinstance(data, dict)
    assert "device" in data
    assert "llm_latency_sec" in data
