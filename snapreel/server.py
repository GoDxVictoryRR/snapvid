"""Web server for the SnapReel UI.

Serves static UI files, handles /generate POST requests in background threads,
streams Server-Sent Events via /events/{job_id}, tests LLM connections via /test_llm,
exposes video /history, /benchmark stats, and serves rendered MP4 files.
Run via: python -m snapreel.server
"""

from __future__ import annotations

import http.server
import json
import logging
import os
from pathlib import Path
import queue
import threading
import time
from typing import Any
import urllib.parse
import uuid

from snapreel.history import load as load_history, save as save_history
from snapreel.llm import test_llm_connection
from snapreel.npu import get_latest_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PORT = 8000
ROOT_DIR = Path(__file__).resolve().parent.parent
UI_DIR = ROOT_DIR / "ui"
OUTPUT_DIR = ROOT_DIR / "output"

_jobs: dict[str, dict[str, Any]] = {}
_job_events: dict[str, list[dict[str, Any]]] = {}
_job_subscribers: dict[str, list[queue.Queue[dict[str, Any]]]] = {}
_sub_lock = threading.Lock()


def _record_event(job_id: str, event: dict[str, Any]) -> None:
    with _sub_lock:
        _job_events.setdefault(job_id, []).append(event)
        for q in _job_subscribers.get(job_id, []):
            q.put(event)


def _subscribe_job_events(job_id: str) -> queue.Queue[dict[str, Any]]:
    q: queue.Queue[dict[str, Any]] = queue.Queue()
    with _sub_lock:
        _job_subscribers.setdefault(job_id, []).append(q)
    return q


def _unsubscribe_job_events(job_id: str, q: queue.Queue[dict[str, Any]]) -> None:
    with _sub_lock:
        if job_id in _job_subscribers and q in _job_subscribers[job_id]:
            _job_subscribers[job_id].remove(q)


def _get_job_events(job_id: str) -> list[dict[str, Any]]:
    with _sub_lock:
        return list(_job_events.get(job_id, []))


def _run_job(topic: str, out_path: str, job_id: str, settings: dict[str, Any] | None = None) -> None:
    settings = settings or {}
    _jobs[job_id] = {"state": "running", "progress": 5, "status": "Planning script with LLM..."}

    for env_k, k in [("LLM_BASE_URL", "llm_base_url"), ("LLM_MODEL", "llm_model"), ("LLM_API_KEY", "llm_api_key"), ("TTS_ENGINE", "tts_engine"), ("TTS_VOICE", "tts_voice")]:
        v = settings.get(k)
        if v is not None and str(v).strip():
            os.environ[env_k] = str(v).strip()

    quality_review = settings.get("quality_pass")
    tts_engine = settings.get("tts_engine", "auto")
    tts_voice = settings.get("tts_voice", "auto")

    try:
        from snapreel.planner import generate
        from snapreel.renderer import render_video
        from snapreel.tts import narrate

        def on_event(ev: dict[str, Any]) -> None:
            _record_event(job_id, ev)

        _record_event(job_id, {"type": "planning_start", "data": {"topic": topic}})
        script = generate(topic, on_event=on_event, quality_review=quality_review)

        _jobs[job_id].update({"progress": 25, "status": f"Script planned: {len(script.scenes)} scenes"})
        out_file = Path(out_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        audio_path = None
        full_narration = " ... ".join(s.narration for s in script.scenes if s.narration)
        if full_narration:
            wav_path = str(out_file.with_suffix(".wav"))
            _jobs[job_id]["status"] = "Generating voice narration..."
            _record_event(job_id, {"type": "tts_start", "data": {"engine": tts_engine, "voice": tts_voice}})
            try:
                dur = narrate(full_narration, wav_path, engine=tts_engine, voice=tts_voice)
                if Path(wav_path).exists() and Path(wav_path).stat().st_size > 0:
                    audio_path = wav_path
                    _record_event(job_id, {"type": "tts_done", "data": {"duration": round(dur, 2)}})
            except Exception as e:
                logger.warning("TTS audio skipped: %s", e)

        total = len(script.scenes)

        def on_progress(i: int, total_cnt: int) -> None:
            pct = 25 + int(round(((i + 1) / total_cnt) * 73))
            _jobs[job_id].update({"progress": min(98, pct), "status": f"Rendering scene {i + 1}/{total_cnt}..."})
            _record_event(job_id, {"type": "render_progress", "data": {"scene": i + 1, "total": total_cnt, "percent": pct}})

        _jobs[job_id]["status"] = f"Rendering {total} video scenes..."
        render_video(script, str(out_file), audio_path=audio_path, on_progress=on_progress)

        save_history(topic, f"/output/{out_file.name}", total)
        _jobs[job_id] = {"state": "done", "progress": 100, "status": "Rendering complete!", "output": f"/output/{out_file.name}"}
        _record_event(job_id, {"type": "done", "data": {"output": f"/output/{out_file.name}", "scenes": total}})
        logger.info("Job %s finished: %s", job_id, out_file)
    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, exc)
        _jobs[job_id] = {"state": "error", "error": str(exc), "progress": 0, "status": "Failed"}
        _record_event(job_id, {"type": "error", "data": {"error": str(exc)}})


class Handler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for SnapReel API, SSE streaming, and UI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8", errors="ignore") if length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        if self.path == "/generate":
            topic = body.get("topic", "").strip()
            if not topic:
                self._json(400, {"error": "topic is required"})
                return

            job_id = str(uuid.uuid4())[:8]
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = str(OUTPUT_DIR / f"{job_id}.mp4")

            threading.Thread(target=_run_job, args=(topic, out_path, job_id, body), daemon=True).start()
            self._json(202, {"job_id": job_id, "output": f"/output/{job_id}.mp4"})
        elif self.path == "/test_llm":
            res = test_llm_connection(body.get("llm_base_url", ""), body.get("llm_model", ""), body.get("llm_api_key", ""))
            self._json(200, res)
        elif self.path.startswith("/status/"):
            job_id = self.path.split("/")[-1]
            self._json(200, _jobs.get(job_id, {"state": "unknown"}))
        else:
            self._json(404, {"error": "Not found"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/events/"):
            self._stream_events(path.split("/events/")[-1])
        elif path == "/test_llm":
            p = urllib.parse.parse_qs(parsed.query)
            res = test_llm_connection(p.get("llm_base_url", [""])[0], p.get("llm_model", [""])[0], p.get("llm_api_key", [""])[0])
            self._json(200, res)
        elif path == "/history":
            self._json(200, load_history())
        elif path == "/benchmark":
            self._json(200, get_latest_benchmark())
        elif path.startswith("/status/"):
            self._json(200, _jobs.get(path.split("/")[-1], {"state": "unknown"}))
        elif path.startswith("/output/"):
            self._serve_output(path.split("/")[-1])
        else:
            super().do_GET()

    def _serve_output(self, filename: str):
        file_path = OUTPUT_DIR / filename
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")

    def _stream_events(self, job_id: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        q = _subscribe_job_events(job_id)
        try:
            for ev in _get_job_events(job_id):
                self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode("utf-8"))
            self.wfile.flush()

            while True:
                try:
                    ev = q.get(timeout=1.0)
                    self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    if ev.get("type") in ("done", "error"):
                        break
                except queue.Empty:
                    if _jobs.get(job_id, {}).get("state") in ("done", "error"):
                        break
                    try:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                    except Exception:
                        break
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            _unsubscribe_job_events(job_id, q)

    def _json(self, code: int, data: Any):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int = PORT):
    server_address = ("", port)
    httpd = http.server.ThreadingHTTPServer(server_address, Handler)
    logger.info("SnapReel server running on http://localhost:%d", port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
