"""Tests for snapreel/server.py HTTP handler and endpoints."""

from email.message import Message
import io
import json
import pytest
from snapreel.server import Handler, _jobs, _record_event


def _setup_handler(path: str = "", body: bytes = b"") -> tuple[Handler, list[int], list[tuple[str, str]]]:
    """Helper to instantiate and configure a Handler mock with proper typing."""
    handler = Handler.__new__(Handler)
    handler.path = path
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()

    headers = Message()
    if body:
        headers["Content-Length"] = str(len(body))
    handler.headers = headers

    responses: list[int] = []
    headers_sent: list[tuple[str, str]] = []

    def mock_send_response(code: int, message: str | None = None) -> None:
        responses.append(code)

    def mock_send_header(keyword: str, value: str) -> None:
        headers_sent.append((keyword, value))

    def mock_end_headers() -> None:
        pass

    handler.send_response = mock_send_response
    handler.send_header = mock_send_header
    handler.end_headers = mock_end_headers

    return handler, responses, headers_sent


def _get_wfile_bytes(handler: Handler) -> bytes:
    """Helper to extract written bytes from mock handler wfile."""
    assert isinstance(handler.wfile, io.BytesIO)
    return handler.wfile.getvalue()


def test_handler_post_generate_without_topic(mocker):
    """POST /generate without topic returns 400 error."""
    handler, responses, _ = _setup_handler(path="/generate", body=b'{"topic": ""}')
    handler.do_POST()

    assert responses == [400]
    payload = json.loads(_get_wfile_bytes(handler).decode())
    assert "error" in payload


def test_handler_get_status_endpoint(mocker):
    """GET /status/{job_id} returns JSON state."""
    _jobs["testjob1"] = {"state": "running", "progress": 42}

    handler, responses, _ = _setup_handler(path="/status/testjob1")
    handler.do_GET()

    assert responses == [200]
    payload = json.loads(_get_wfile_bytes(handler).decode())
    assert payload["state"] == "running"
    assert payload["progress"] == 42


def test_handler_get_history_endpoint(mocker):
    """GET /history returns video history list."""
    mocker.patch("snapreel.server.load_history", return_value=[{"topic": "Photosynthesis", "path": "/output/1.mp4", "scenes": 5}])

    handler, responses, _ = _setup_handler(path="/history")
    handler.do_GET()

    assert responses == [200]
    payload = json.loads(_get_wfile_bytes(handler).decode())
    assert len(payload) == 1
    assert payload[0]["topic"] == "Photosynthesis"


def test_handler_get_benchmark_endpoint(mocker):
    """GET /benchmark returns benchmark metrics."""
    mocker.patch("snapreel.server.get_latest_benchmark", return_value={"device": "Snapdragon X Elite", "llm_latency_sec": 2.1})

    handler, responses, _ = _setup_handler(path="/benchmark")
    handler.do_GET()

    assert responses == [200]
    payload = json.loads(_get_wfile_bytes(handler).decode())
    assert payload["device"] == "Snapdragon X Elite"


def test_handler_test_llm_success(mocker):
    """POST /test_llm returns ok=true and latency on reachable server."""
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200

    body = json.dumps({"llm_base_url": "http://fake/v1", "llm_model": "test-model"}).encode()
    handler, responses, _ = _setup_handler(path="/test_llm", body=body)
    handler.do_POST()

    assert responses == [200]
    payload = json.loads(_get_wfile_bytes(handler).decode())
    assert payload["ok"] is True
    assert payload["model"] == "test-model"


def test_handler_test_llm_failure(mocker):
    """GET /test_llm with missing parameters returns ok=false."""
    handler, responses, _ = _setup_handler(path="/test_llm?llm_base_url=&llm_model=")
    handler.do_GET()

    assert responses == [200]
    payload = json.loads(_get_wfile_bytes(handler).decode())
    assert payload["ok"] is False


def test_handler_events_sse(mocker):
    """GET /events/{job_id} streams recorded SSE events."""
    job_id = "testjob_sse"
    _jobs[job_id] = {"state": "done"}
    _record_event(job_id, {"type": "planning_start", "data": {"topic": "AI"}})
    _record_event(job_id, {"type": "done", "data": {"output": "/output/test.mp4"}})

    handler, responses, _ = _setup_handler(path=f"/events/{job_id}")
    handler.do_GET()

    assert responses == [200]
    content = _get_wfile_bytes(handler).decode("utf-8")
    assert "data: " in content
    assert "planning_start" in content
    assert "done" in content


def test_handler_get_config(mocker):
    """GET /config returns active configuration."""
    handler, responses, _ = _setup_handler(path="/config")
    handler.do_GET()
    assert responses == [200]
    payload = json.loads(_get_wfile_bytes(handler).decode())
    assert "llm_base_url" in payload
    assert "llm_model" in payload


def test_handler_post_config_updates_env_and_clears_key(mocker):
    """POST /config updates os.environ and clears LLM_API_KEY when passed empty."""
    import os
    os.environ["LLM_API_KEY"] = "old-secret-key"
    body = json.dumps({
        "llm_base_url": "https://integrate.api.nvidia.com/v1",
        "llm_model": "meta/llama-3.1-8b-instruct",
        "llm_api_key": "",
    }).encode()
    handler, responses, _ = _setup_handler(path="/config", body=body)
    handler.do_POST()
    assert responses == [200]
    assert os.environ["LLM_BASE_URL"] == "https://integrate.api.nvidia.com/v1"
    assert os.environ["LLM_MODEL"] == "meta/llama-3.1-8b-instruct"
    assert "LLM_API_KEY" not in os.environ


def test_handler_post_generate_rate_limit(mocker):
    """POST /generate responds with HTTP 429 when rate limit is exceeded."""
    import os
    os.environ["RATE_LIMIT_PER_HOUR"] = "2"
    from snapreel.server import _ip_request_timestamps
    _ip_request_timestamps.clear()

    # Request 1: OK
    h1, r1, _ = _setup_handler(path="/generate", body=b'{"topic": "Test 1"}')
    h1.client_address = ("192.168.1.100", 12345)
    mocker.patch("threading.Thread.start")
    h1.do_POST()
    assert r1 == [202]

    # Request 2: OK
    h2, r2, _ = _setup_handler(path="/generate", body=b'{"topic": "Test 2"}')
    h2.client_address = ("192.168.1.100", 12345)
    h2.do_POST()
    assert r2 == [202]

    # Request 3: Blocked (429)
    h3, r3, _ = _setup_handler(path="/generate", body=b'{"topic": "Test 3"}')
    h3.client_address = ("192.168.1.100", 12345)
    h3.do_POST()
    assert r3 == [429]
    payload = json.loads(_get_wfile_bytes(h3).decode())
    assert "Rate limit" in payload.get("error", "")

    # Cleanup
    os.environ["RATE_LIMIT_PER_HOUR"] = "10"
    _ip_request_timestamps.clear()

