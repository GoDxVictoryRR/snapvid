# SnapReel 🎬

> Offline agentic explainer-video maker running local-first on Snapdragon NPU & local LLMs with pure-Python rendering and zero cloud runtime dependencies.

---

## Overview

**SnapReel** turns complex concepts and notes into punchy, beautifully animated 720p explainer videos. Unlike traditional video pipelines that depend on heavy browser automation (Remotion), LaTeX/Cairo environments (Manim), or cloud rendering services, SnapReel is built entirely in Python using **Pillow, NumPy, and bundled FFmpeg**. 

It runs completely offline using local models (Qualcomm GenieX on Snapdragon NPU, Ollama, or llama.cpp) and can switch to any cloud OpenAI-compatible endpoint with a single configuration line.

---

## Architecture

```
User Prompt (CLI / Web UI)
         │
         ▼
┌──────────────────────────────┐
│  SnapReel Planner & LLM      │ ◄─── Configuration (.env)
│  (llm.py / planner.py)       │      • Ollama (qwen2.5:3b)
└──────────────┬───────────────┘      • GenieX NPU (Qwen3-4B-Instruct)
               │ (Raw JSON)           • Cloud (OpenAI / Groq)
               ▼
┌──────────────────────────────┐
│  Schema Validation & Repair  │ ◄─── Pydantic v2 (schema.py)
│  (Up to 3-retry Repair Loop) │      • Validates duration, templates,
└──────────────┬───────────────┘        data models, & total timing
               │ (Validated SceneScript)
               ▼
┌──────────────────────────────┐
│  Pure-Python Frame Renderer  │ ◄─── Pillow + NumPy (templates/)
│  (renderer.py)               │      • Title, Bullets, Bar Chart,
└──────────────┬───────────────┘        Counter, Code Block, Kinetic
               │ (Raw 1280x720 RGB frames piped)
               ▼
┌──────────────────────────────┐
│  FFmpeg Subprocess Pipeline  │ ◄─── imageio-ffmpeg binary
│  (H.264 / AAC 30 FPS MP4)    │ ◄─── Windows SAPI TTS (tts.py)
└──────────────┬───────────────┘
               │
               ▼
       output/*.mp4 Video
```

---

## Key Features

- **Local-First & Offline**: Zero runtime cloud calls needed. Runs locally on Snapdragon X Series laptops via Qualcomm GenieX or standard local runners like Ollama.
- **Agentic Self-Correction**: Implements an automatic schema validation and repair loop (up to 3 retries) feeding Pydantic errors back to the LLM when invalid scene structures are emitted.
- **Pure-Python Renderer**: No Node.js, no Chromium headless shells, no Manim/Cairo complications. Fast Pillow + NumPy frame drawing piped directly to bundled FFmpeg.
- **Six Curated Templates**:
  - `title`: Centered cards with slide-up easing and accent gradient rules.
  - `bullets`: Staggered reveals with glowing markers and clean typography.
  - `bar_chart`: Animated horizontal comparative bars with proportional scaling.
  - `counter`: Large eased metric counter with prefix/suffix unit labels.
  - `code_block`: Dark theme syntax highlighting with auto-scroll for long snippets.
  - `kinetic`: Alternating color typography with dynamic pop-in scaling.
- **Windows Built-in TTS**: Leverages Windows SAPI via `win32com` for offline voice narration with proportional caption timestamps.
- **Modern Web Interface**: Built-in dark mode dashboard served by `python -m snapreel.server`.

---

## Quick Start

### 1. Prerequisites
- Python 3.11+ (Python 3.11, 3.12, 3.13 tested)
- Windows (recommended for SAPI TTS) or Linux/macOS

### 2. Installation
```bash
git clone https://github.com/GoDxVictoryRR/snapvid.git
cd snapvid

# Install dependencies (bundles ffmpeg automatically)
pip install -r requirements.txt
```

### 3. Configure LLM Backend
Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` for your preferred model:
```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
LLM_API_KEY=
LLM_TIMEOUT=60
```

### 4. Generate Videos

**Via Command Line (CLI):**
```bash
python run.py "Explain quantum superposition in 45 seconds"
```
The rendered video will be saved to `output/<slug>_<timestamp>.mp4`.

**Via Web UI:**
```bash
python -m snapreel.server
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Supported LLM Backends

Switch backends effortlessly by changing `LLM_BASE_URL` and `LLM_MODEL` in `.env`:

| Backend | `LLM_BASE_URL` | `LLM_MODEL` Example | Acceleration |
|---|---|---|---|
| **Qualcomm GenieX** | `http://localhost:8080/v1` | `Qwen3-4B-Instruct-2507` | **Snapdragon NPU** |
| **Ollama (Local)** | `http://localhost:11434/v1` | `qwen2.5:3b` | CPU / GPU |
| **llama.cpp server** | `http://localhost:8080/v1` | Any GGUF model loaded | CPU / Vulkan |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini` | Cloud |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` | Cloud LPU |
| **Together AI** | `https://api.together.xyz/v1` | `Qwen/Qwen2.5-7B-Instruct` | Cloud GPU |

---

## Environment Variables

| Variable | Description | Default / Example |
|---|---|---|
| `LLM_BASE_URL` | OpenAI-compatible base endpoint URL | `http://localhost:11434/v1` |
| `LLM_MODEL` | Target model identifier | `qwen2.5:3b` |
| `LLM_API_KEY` | Optional authorization key (empty for local) | *(empty)* |
| `LLM_TIMEOUT` | Timeout in seconds for HTTP generation calls | `60` |

---

## Testing

Run the comprehensive unit test suite:
```bash
python -m pytest tests/ -v
```

The test suite covers:
- **`tests/test_schema.py`**: 11 Pydantic validation checks (template types, bounds, durations, malformed JSON).
- **`tests/test_llm.py`**: 5 mocked LLM completion, error propagation, and repair loop tests.
- **`tests/test_renderer.py`**: 7 frame rendering, template timing, and FFmpeg pipe tests.
- **`tests/test_tts.py`**: 3 Windows SAPI and proportional caption timing tests.
- **`tests/test_planner.py`**: 3 prompt assembly and planning delegation tests.
- **`tests/test_server.py`**: HTTP server endpoint tests.

---

## Limitations

- **On-Device NPU Acceleration**: NPU acceleration via GenieX requires Windows on Snapdragon hardware (Qualcomm Snapdragon X Elite / Plus). On x86/other systems, Ollama or cloud models serve as transparent drop-in fallbacks.
- **Voice Narration (TTS)**: Native zero-dependency TTS uses Windows SAPI via `win32com`. On non-Windows platforms, TTS gracefully falls back to video-only generation.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
