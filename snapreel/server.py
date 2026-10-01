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
import math
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

PORT = int(os.environ.get("PORT", 8000))
ROOT_DIR = Path(__file__).resolve().parent.parent
UI_DIR, OUTPUT_DIR = ROOT_DIR / "ui", ROOT_DIR / "output"

_jobs: dict[str, dict[str, Any]] = {}
_job_events: dict[str, list[dict[str, Any]]] = {}
_job_subscribers: dict[str, list[queue.Queue[dict[str, Any]]]] = {}
_sub_lock = threading.Lock()

_rate_limit_lock = threading.Lock()
_ip_request_timestamps: dict[str, list[float]] = {}


def _get_client_ip(handler: Any) -> str:
    """Extract client IP respecting reverse-proxy headers like X-Forwarded-For."""
    if hasattr(handler, "headers") and handler.headers:
        xff = handler.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
    return getattr(handler, "client_address", ["127.0.0.1"])[0]


def _check_rate_limit(ip: str) -> tuple[bool, int]:
    """Check if IP has exceeded allowed generations per hour.

    Returns (is_allowed, seconds_to_retry).
    Configurable via RATE_LIMIT_PER_HOUR env var (default: 10, set 0 to disable).
    """
    try:
        limit = int(os.environ.get("RATE_LIMIT_PER_HOUR", 10))
    except ValueError:
        limit = 10
    if limit <= 0:
        return True, 0

    now = time.time()
    window = 3600.0
    with _rate_limit_lock:
        timestamps = [t for t in _ip_request_timestamps.get(ip, []) if now - t < window]
        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(window - (now - oldest)))
            _ip_request_timestamps[ip] = timestamps
            return False, retry_after
        timestamps.append(now)
        _ip_request_timestamps[ip] = timestamps
        return True, 0


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

    env_keys = [("LLM_BASE_URL", "llm_base_url"), ("LLM_MODEL", "llm_model"), ("LLM_API_KEY", "llm_api_key"),
                ("LLM_TIMEOUT", "llm_timeout"), ("TTS_ENGINE", "tts_engine"), ("TTS_VOICE", "tts_voice")]
    for env_k, k in env_keys:
        if k in settings:
            v = str(settings[k] or "").strip()
            if v and "..." not in v and v != "***":
                os.environ[env_k] = v
            elif env_k == "LLM_API_KEY" and v == "":
                # Do NOT clear server environment key if client simply left it blank
                pass


    if not settings.get("llm_timeout"):
        model, cur = os.environ.get("LLM_MODEL", ""), int(os.environ.get("LLM_TIMEOUT", 300))
        if any(x in model.lower() for x in ["hf.co/", "fable", "qwen3.5", "opus", "31b", "70b"]):
            os.environ["LLM_TIMEOUT"] = str(max(cur, 300))

    quality_review, tts_engine, tts_voice = settings.get("quality_pass"), settings.get("tts_engine", "auto"), settings.get("tts_voice", "auto")
    target_duration, aspect_ratio = int(settings.get("target_duration") or 60), str(settings.get("aspect_ratio") or "16:9")

    try:
        from snapreel.planner import generate
        from snapreel.renderer import render_video
        from snapreel.tts import concat_audio, prepare_audio, reconcile_durations

        def on_event(ev: dict[str, Any]) -> None:
            _record_event(job_id, ev)

        _record_event(job_id, {"type": "planning_start", "data": {"topic": topic}})
        script = generate(topic, on_event=on_event, quality_review=quality_review, target_duration=target_duration, aspect_ratio=aspect_ratio)

        _jobs[job_id].update({"progress": 25, "status": f"Script planned: {len(script.scenes)} scenes"})
        out_file = Path(out_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        audio_path, audio_durations = None, None
        has_narration = any(s.narration and s.narration.strip() for s in script.scenes)
        def _quantize_frames(scs: list[Any], tgt_dur: float) -> float:
            from snapreel.renderer import RENDER_FPS
            tgt_f, raw_f = round(tgt_dur * RENDER_FPS), [max(1, round(s.duration * RENDER_FPS)) for s in scs]
            if (diff := tgt_f - sum(raw_f)) != 0 and raw_f:
                raw_f[-1] = max(1, raw_f[-1] + diff)
            for idx, s in enumerate(scs):
                s.duration = round(raw_f[idx] / RENDER_FPS, 4)
            return round(sum(s.duration for s in scs), 4)

        if has_narration:
            wav_dir = out_file.parent / f"{job_id}_audio"
            wav_dir.mkdir(parents=True, exist_ok=True)
            wav_path = str(out_file.with_suffix(".wav"))
            _jobs[job_id]["status"] = "Generating voice narration..."
            _record_event(job_id, {"type": "tts_start", "data": {"engine": tts_engine, "voice": tts_voice}})
            try:
                wav_paths, audio_durations = prepare_audio(script, str(wav_dir), engine=tts_engine, voice=tts_voice)
                script = reconcile_durations(script, audio_durations, min_tail_padding=0.8, max_trailing_pause=1.4, target_duration=float(target_duration))
                script.total_duration = _quantize_frames(script.scenes, float(target_duration))
                scene_durations = [s.duration for s in script.scenes]
                concat_audio(wav_paths, scene_durations, wav_path)
                if Path(wav_path).exists() and Path(wav_path).stat().st_size > 44:
                    audio_path = wav_path
                    _record_event(job_id, {"type": "tts_done", "data": {
                        "duration": round(sum(scene_durations), 2), "narration_duration": round(sum(audio_durations), 2),
                    }})
            except Exception as e:
                logger.warning("TTS audio generation skipped: %s", e)
        else:
            script.total_duration = _quantize_frames(script.scenes, float(target_duration))

        total = len(script.scenes)

        def on_progress(i: int, total_cnt: int) -> None:
            pct = 25 + round(((i + 1) / total_cnt) * 73)
            _jobs[job_id].update({"progress": min(98, pct), "status": f"Rendering scene {i + 1}/{total_cnt}..."})
            _record_event(job_id, {"type": "render_progress", "data": {"scene": i + 1, "total": total_cnt, "percent": pct}})

        _jobs[job_id]["status"] = f"Rendering {total} video scenes..."
        render_video(script, str(out_file), audio_path=audio_path, on_progress=on_progress, audio_durations=audio_durations)

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
            client_ip = _get_client_ip(self)
            allowed, retry_after = _check_rate_limit(client_ip)
            if not allowed:
                self._json(429, {"error": f"Rate limit reached. Please wait {retry_after}s before creating another video."})
                return

            active_cnt = sum(1 for j in _jobs.values() if j.get("state") == "running")
            max_conc = int(os.environ.get("MAX_CONCURRENT_JOBS", 2))
            if active_cnt >= max_conc:
                self._json(429, {"error": "Server is currently rendering another video. Please wait a moment and try again."})
                return

            topic = body.get("topic", "").strip()
            if not topic:
                self._json(400, {"error": "topic is required"})
                return

            job_id = str(uuid.uuid4())[:8]
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = str(OUTPUT_DIR / f"{job_id}.mp4")
            threading.Thread(target=_run_job, args=(topic, out_path, job_id, body), daemon=True).start()
            self._json(202, {"job_id": job_id, "output": f"/output/{job_id}.mp4"})
        elif self.path == "/config":
            for ek, k in [("LLM_BASE_URL", "llm_base_url"), ("LLM_MODEL", "llm_model"), ("LLM_API_KEY", "llm_api_key"), ("TTS_ENGINE", "tts_engine"), ("TTS_VOICE", "tts_voice")]:
                if k in body:
                    v = str(body[k] or "").strip()
                    if v and "••••" not in v and "..." not in v:
                        os.environ[ek] = v
                    elif ek == "LLM_API_KEY" and v == "":
                        os.environ.pop(ek, None)
            self._json(200, {"ok": True})
        elif self.path == "/test_llm":
            key = body.get("llm_api_key", "").strip()
            if not key or "••••" in key or "..." in key or key == "***":
                key = os.environ.get("LLM_API_KEY", "")
            res = test_llm_connection(body.get("llm_base_url", ""), body.get("llm_model", ""), key)
            self._json(200, res)
        elif self.path.startswith("/status/"):
            self._json(200, _jobs.get(self.path.split("/")[-1], {"state": "unknown"}))
        else:
            self._json(404, {"error": "Not found"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/events/"):
            self._stream_events(path.split("/events/")[-1])
        elif path == "/config":
            raw_key = os.environ.get("LLM_API_KEY", "")
            masked_key = (raw_key[:4] + "••••" + raw_key[-4:]) if len(raw_key) > 8 else ("••••••••" if raw_key else "")
            self._json(200, {
                "llm_base_url": os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
                "llm_model": os.environ.get("LLM_MODEL", "qwen2.5:3b"),
                "llm_api_key": masked_key,
                "has_api_key": bool(raw_key),
                "tts_engine": os.environ.get("TTS_ENGINE", "auto"),
                "tts_voice": os.environ.get("TTS_VOICE", "auto"),
            })
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
            for h, v in [("Content-Type", "video/mp4"), ("Content-Length", str(file_path.stat().st_size))]:
                self.send_header(h, v)
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")

    def _stream_events(self, job_id: str):
        self.send_response(200)
        for h, v in [("Content-Type", "text/event-stream"), ("Cache-Control", "no-cache"),
                     ("Connection", "keep-alive"), ("Access-Control-Allow-Origin", "*")]:
            self.send_header(h, v)
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
        for h, v in [("Content-Type", "application/json"), ("Content-Length", str(len(body)))]:
            self.send_header(h, v)
        self.end_headers()
        self.wfile.write(body)


class _SnapReelServer(http.server.ThreadingHTTPServer):
    """ThreadingHTTPServer that cleanly handles client disconnects on Windows."""

    def handle_error(self, request: Any, client_address: Any) -> None:
        import sys
        if sys.exc_info()[0] in (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return
        super().handle_error(request, client_address)


def run_server(port: int = PORT):
    httpd = _SnapReelServer(("", port), Handler)
    logger.info("SnapReel server running on http://localhost:%d", port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
