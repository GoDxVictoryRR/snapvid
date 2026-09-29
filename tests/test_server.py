"""Tests for snapreel/server.py HTTP handler and endpoints."""

import io
import json
import pytest
from snapreel.server import Handler, _jobs, _record_event


def test_handler_post_generate_without_topic(mocker):
    """POST /generate without topic returns 400 error."""
    handler = Handler.__new__(Handler)
    handler.rfile = io.BytesIO(b'{"topic": ""}')
    handler.headers = {"Content-Length": "14"}
    handler.path = "/generate"
    handler.wfile = io.BytesIO()

    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda name, val: None
    handler.end_headers = lambda: None

    handler.do_POST()

    assert responses == [400]
    payload = json.loads(handler.wfile.getvalue().decode())
    assert "error" in payload


def test_handler_get_status_endpoint(mocker):
    """GET /status/{job_id} returns JSON state."""
    _jobs["testjob1"] = {"state": "running", "progress": 42}

    handler = Handler.__new__(Handler)
    handler.path = "/status/testjob1"
    handler.wfile = io.BytesIO()

    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda name, val: None
    handler.end_headers = lambda: None

    handler.do_GET()

    assert responses == [200]
    payload = json.loads(handler.wfile.getvalue().decode())
    assert payload["state"] == "running"
    assert payload["progress"] == 42


def test_handler_get_history_endpoint(mocker):
    """GET /history returns video history list."""
    mocker.patch("snapreel.server.load_history", return_value=[{"topic": "Photosynthesis", "path": "/output/1.mp4", "scenes": 5}])

    handler = Handler.__new__(Handler)
    handler.path = "/history"
    handler.wfile = io.BytesIO()

    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda name, val: None
    handler.end_headers = lambda: None

    handler.do_GET()

    assert responses == [200]
    payload = json.loads(handler.wfile.getvalue().decode())
    assert len(payload) == 1
    assert payload[0]["topic"] == "Photosynthesis"


def test_handler_get_benchmark_endpoint(mocker):
    """GET /benchmark returns benchmark metrics."""
    mocker.patch("snapreel.server.get_latest_benchmark", return_value={"device": "Snapdragon X Elite", "llm_latency_sec": 2.1})

    handler = Handler.__new__(Handler)
    handler.path = "/benchmark"
    handler.wfile = io.BytesIO()

    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda name, val: None
    handler.end_headers = lambda: None

    handler.do_GET()

    assert responses == [200]
    payload = json.loads(handler.wfile.getvalue().decode())
    assert payload["device"] == "Snapdragon X Elite"


def test_handler_test_llm_success(mocker):
    """POST /test_llm returns ok=true and latency on reachable server."""
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200

    handler = Handler.__new__(Handler)
    body = json.dumps({"llm_base_url": "http://fake/v1", "llm_model": "test-model"}).encode()
    handler.rfile = io.BytesIO(body)
    handler.headers = {"Content-Length": str(len(body))}
    handler.path = "/test_llm"
    handler.wfile = io.BytesIO()

    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda name, val: None
    handler.end_headers = lambda: None

    handler.do_POST()

    assert responses == [200]
    payload = json.loads(handler.wfile.getvalue().decode())
    assert payload["ok"] is True
    assert payload["model"] == "test-model"


def test_handler_test_llm_failure(mocker):
    """GET /test_llm with missing parameters returns ok=false."""
    handler = Handler.__new__(Handler)
    handler.path = "/test_llm?llm_base_url=&llm_model="
    handler.wfile = io.BytesIO()

    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda name, val: None
    handler.end_headers = lambda: None

    handler.do_GET()

    assert responses == [200]
    payload = json.loads(handler.wfile.getvalue().decode())
    assert payload["ok"] is False


def test_handler_events_sse(mocker):
    """GET /events/{job_id} streams recorded SSE events."""
    job_id = "testjob_sse"
    _jobs[job_id] = {"state": "done"}
    _record_event(job_id, {"type": "planning_start", "data": {"topic": "AI"}})
    _record_event(job_id, {"type": "done", "data": {"output": "/output/test.mp4"}})

    handler = Handler.__new__(Handler)
    handler.path = f"/events/{job_id}"
    handler.wfile = io.BytesIO()

    responses = []
    headers = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda name, val: headers.append((name, val))
    handler.end_headers = lambda: None

    handler.do_GET()

    assert responses == [200]
    content = handler.wfile.getvalue().decode("utf-8")
    assert "data: " in content
    assert "planning_start" in content
    assert "done" in content
