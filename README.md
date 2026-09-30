# SnapVid 🎬

> **Local-First Agentic Explainer-Video Maker**  
> Transform text prompts, research papers, and complex topics into synchronized, broadcast-grade animated explainer videos in minutes — running locally on Snapdragon NPU & edge LLMs with a pure-Python rendering engine. Zero cloud runtime dependencies.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-74%20passed-success.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hardware Acceleration](https://img.shields.io/badge/Accelerated%20by-Qualcomm%20Snapdragon%20NPU-E00000.svg)](https://aihub.qualcomm.com/)
[![Zero Node.js](https://img.shields.io/badge/runtime-Pure%20Python%20%2B%20FFmpeg-green.svg)](#architecture)

---

## 📑 Table of Contents

- [Overview](#overview)
- [Key Architectural Highlights](#key-architectural-highlights)
- [Interactive Web Studio UI](#interactive-web-studio-ui)
- [System Architecture](#system-architecture)
- [Visual Templates](#visual-templates)
- [Aspect Ratios & Output Formats](#aspect-ratios--output-formats)
- [Audio & Dynamic Karaoke Captions](#audio--dynamic-karaoke-captions)
- [Supported LLM Backends](#supported-llm-backends)
- [Snapdragon NPU Acceleration & Benchmarks](#snapdragon-npu-acceleration--benchmarks)
- [Quick Start](#quick-start)
  - [Prerequisites](#1-prerequisites)
  - [Installation](#2-installation)
  - [Configuration](#3-configuration)
  - [Running SnapVid](#4-running-snapvid)
- [Python API Usage](#python-api-usage)
- [Repository Structure](#repository-structure)
- [Test Suite & Quality Verification](#test-suite--quality-verification)
- [License](#license)

---

## Overview

**SnapVid** is an end-to-end agentic video production engine that automates the entire creative and technical pipeline of explainer-video generation: **script planning, multi-speaker or single-narrator pacing, visual scene sequencing, audio narration, dynamic karaoke captioning, transition effects, and video compositing.**

Traditional programmatic video tools like Remotion or Manim require heavy browser automation (Node.js/Puppeteer) or complex graphic subsystems (Cairo/LaTeX). Cloud generative video platforms lock users behind subscription walls, watermarks, slow rendering queues, and data privacy risks.

SnapVid takes a fundamentally different approach:
- **Local-First & Private:** Runs entirely on your local machine using edge language models (Snapdragon Hexagon NPU via Qualcomm GenieX, Ollama, or llama.cpp) and offline TTS engines.
- **Pure Python + Bundled FFmpeg:** Fast frame rendering using Pillow and NumPy piped directly into an imageio-ffmpeg subprocess at 30 FPS.
- **Audio-First Precision Sync:** Voice narration is synthesized *first*, scene timings and visual keyframes are automatically adjusted to match real human cadence, and word-level highlighted captions are burned in seamlessly.
- **Self-Healing LLM Loop:** Malformed JSON outputs from small language models are automatically repaired in-flight via structured Pydantic v2 validation errors (up to 3 retries).

---

## Key Architectural Highlights

| Feature | Description |
|---|---|
| **Two-Agent Pipeline** | **Scene Planner Agent** drafts pacing and layout; **Quality Critic Agent** polishes narrative flow and visual variety before rendering. |
| **Self-Healing Validation** | Strict Pydantic v2 schemas reject malformed JSON, automatically passing validation traceback back to the LLM for instant targeted correction. |
| **Audio-First Synchronization** | Solves video-narration desynchronization. Speech is generated and measured first; scene durations dynamically scale with proportional buffer padding. |
| **Word-Level Karaoke Captions** | Dynamic bottom-anchored subtitle badges with active word highlighting, bounded padding, and automatic canvas-aware line wrapping. |
| **10 Motion Graphic Templates** | Purpose-built animations for technical concepts, quantitative metrics, code explanations, quotes, bullet points, and comparative data. |
| **Seamless Scene Transitions** | Multi-mode transition compositor (Fade, Slide, Zoom, Cross-dissolve) smoothly blending neighboring scenes without frame dropping. |
| **Multi-Aspect Ratio Canvas** | Native multi-canvas coordinate engine supporting 16:9 Landscape, 9:16 Mobile Vertical (Shorts/Reels/TikTok), and 1:1 Square Feeds. |
| **NPU Acceleration** | Native integration with Qualcomm Snapdragon X Series Hexagon NPU running quantized Qwen3-4B models at ~22.4 tokens/second. |

---

## Interactive Web Studio UI

SnapVid includes a full-featured browser-based workspace styled in modern dark glassmorphism:

- **Prompt & Video Settings:** Configure topic, duration (30s, 60s, 120s, 300s), aspect ratio (`16:9`, `9:16`, `1:1`), and transition effects.
- **Real-Time Agent Activity Tracker:** Live Server-Sent Events (SSE) stream LLM planning steps, token generation metrics, TTS generation state, and frame render percentages.
- **Live Video Player:** Instant in-browser playback, loop control, and single-click direct MP4 downloads.
- **Dynamic Settings Drawer:** Override LLM providers (Ollama, Qualcomm GenieX, OpenAI, Groq, Together AI, Google Gemini, NVIDIA NIM), custom Base URLs, and API keys without restarting the server.
- **Test Connections:** Live ping buttons to verify LLM connectivity and TTS voice playback directly from the interface.
- **Generation History Drawer:** Search and re-watch previously generated explainer videos stored locally in `output/`.

---

## System Architecture

```
User Prompt (Web UI / CLI / Python API)
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Agentic Planning Layer (snapreel/planner.py & llm.py)       │
│  • Primary Model: Qualcomm GenieX NPU / Ollama / Cloud LLM   │
│  • Self-Healing Loop: Pydantic v2 JSON Schema Repair         │
│  • Quality Critic Agent: Flow, variety, and cadence review   │
└──────────────────────────────┬───────────────────────────────┘
                               │ Validated SceneScript (JSON)
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Audio & Synchronization Pipeline (snapreel/tts.py)          │
│  • Multi-Engine TTS: Kokoro Neural ➔ Edge TTS ➔ SAPI         │
│  • Audio Pre-computation: Scene audio rendered & measured    │
│  • Duration Reconciliation: Scenes dynamically resized       │
│  • Word-Level Timing Extraction: Dynamic karaoke captions    │
└──────────────────────────────┬───────────────────────────────┘
                               │ Synchronized Timeline
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Pure-Python Frame Renderer (snapreel/renderer.py)           │
│  • 10 Animated Motion Graphic Templates (templates/)         │
│  • Aspect Ratio Adapter: 16:9, 9:16, 1:1 Canvas Coordinates  │
│  • Scene Transitions: Fade, Slide, Zoom, Cross-Dissolve      │
│  • Dynamic Subtitle Overlay with Word-Level Active Glow      │
└──────────────────────────────┬───────────────────────────────┘
                               │ Raw RGB Frames piped via stdin
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  FFmpeg Subprocess Compositor (imageio-ffmpeg)               │
│  • H.264 Video Encoder @ 30 FPS                              │
│  • High-Fidelity AAC Audio Multiplexer                       │
│  • Optimized MP4 Container (Faststart enabled)               │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                  Finished output/<slug>.mp4
```

---

## Visual Templates

SnapVid includes 10 algorithmic animation templates, designed to display complex information cleanly without text overflow or visual clipping across all aspect ratios:

| Template | Primary Use Case | Animation Style |
|---|---|---|
| `title` | Video intro, hook, and conclusion cards | Slide-up card easing, pulsing accent gradient badge, typography reveal. |
| `bullets` | Sequential points, agendas, feature lists | Staggered item entry, glowing bullet nodes, subtitle-synchronized reveals. |
| `bar_chart` | Quantities, performance comparisons, metrics | Smooth bar growth with proportional metric scaling and percentage badges. |
| `counter` | Statistics, KPIs, percentages, revenue figures | Eased numeric counter rolling smoothly from zero to target value. |
| `code_block` | Code snippets, terminal commands, configurations | Dark syntax container with line numbers, code glow, and auto-scrolling. |
| `kinetic` | Dramatic quotes, power words, high-impact hooks | Dynamic scale pop-in with alternating accent color emphasis. |
| `lower_third` | Speaker titles, topic alerts, chapter callouts | Sleek bottom-corner informational banner with smooth horizontal slide. |
| `quote` | Expert testimonials, insights, philosophies | Large quotation marks, italicized body text, and author attribution card. |
| `icon_list` | Feature grids, step-by-step guides, benefits | Pill cards with colored glyph tags and hierarchical descriptive copy. |
| `split` | Before/After, Pros/Cons, Two-sided comparisons | Dual-column side-by-side comparison layout with distinct colored cards. |

---

## Aspect Ratios & Output Formats

SnapVid automatically recalculates layout bounds, typography sizes, margin safety zones, and element positions based on the selected aspect ratio:

| Aspect Ratio | Resolution | Optimal Target Platform | Layout Adjustments |
|---|---|---|---|
| **16:9** | 1280 × 720 | YouTube, Desktop, TV, Presentation Decks | Wide landscape layout, generous horizontal spacing. |
| **9:16** | 720 × 1280 | YouTube Shorts, Instagram Reels, TikTok | Vertical mobile orientation, larger fonts, safe padding margins. |
| **1:1** | 720 × 720 | LinkedIn Feed, Twitter / X, Instagram Square | Centered square canvas, compact balanced composition. |

---

## Audio & Dynamic Karaoke Captions

Unlike conventional tools that render video frames at arbitrary predetermined speeds and then force audio to stretch or clip, **SnapVid implements an Audio-First Pipeline**:

1. **Pre-generation:** Scene voice narration is generated upfront using the auto-selected TTS engine:
   - **Kokoro-82M:** Offline, ultra-lightweight neural speech running locally on CPU.
   - **Edge TTS:** High-fidelity neural voice with extensive accent selections (online).
   - **Windows SAPI:** Instant offline fallback native to Windows OS.
2. **Dynamic Duration Reconciliation:** Actual audio duration is measured with millisecond precision. Scene keyframes and transition windows are proportionally stretched so video visuals never end abruptly before the speaker finishes.
3. **Word-Level Subtitle Highlights:** The caption engine segments speech into word groups, tracks cumulative audio progress, and displays a sleek bottom badge with the active word dynamically illuminated.

---

## Supported LLM Backends

SnapVid communicates through an OpenAI-compatible interface, allowing seamless switching between local and cloud providers:

| Provider | Endpoint (`LLM_BASE_URL`) | Default Model | Mode | Notes |
|---|---|---|---|---|
| **Qualcomm GenieX** | `http://localhost:8080/v1` | `Qwen3-4B-Instruct-2507` | Local (NPU) | Optimized for Snapdragon Hexagon NPU. |
| **Ollama** | `http://localhost:11434/v1` | `qwen2.5:3b` or `llama3.2` | Local (CPU/GPU) | Popular zero-config local engine. |
| **llama.cpp / vLLM** | `http://localhost:8080/v1` | Any loaded model | Local | Fast GGUF / AWQ inference server. |
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-1.5-flash` | Cloud | Fast cloud intelligence with OpenAI API schema. |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | `meta/llama-3.1-8b-instruct` | Cloud | High-speed enterprise accelerated inference. |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` | Cloud LPU | Ultra-fast ~500 tok/sec inference. |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini` | Cloud | Standard hosted OpenAI endpoint. |
| **Together AI** | `https://api.together.xyz/v1` | `Qwen/Qwen2.5-7B-Instruct` | Cloud GPU | Broad open-weights catalog. |

---

## Snapdragon NPU Acceleration & Benchmarks

SnapVid is deeply optimized for Windows on Snapdragon devices powered by the **Snapdragon X Elite and Snapdragon X Plus** platforms.

By offloading the language model generation to the **Hexagon NPU** via Qualcomm GenieX using w4a16 quantization, SnapVid runs end-to-end video creation with low thermal overhead and minimal battery consumption:

| Pipeline Stage | Processing Unit | Latency | Efficiency |
|---|---|---|---|
| **Scene Script Generation (Qwen3-4B)** | **Snapdragon Hexagon NPU** | **~2.1s** | **~22.4 tokens/sec** |
| Quality Critic Refinement | **Snapdragon Hexagon NPU** | **~1.8s** | Zero CPU thermal throttling |
| Kokoro Neural Audio Narration | CPU (ARM64) | ~1.6s / scene | 1.4× real-time speed |
| Pure-Python Frame Drawing | CPU (Pillow + NumPy) | ~0.5s / scene | 30 FPS native pipe |
| **Full 60s Explainer Video** | **Snapdragon X Elite** | **~28s total** | **> 2× Real-Time Delivery** |

### Profiling via Qualcomm AI Hub
Inspect and profile models on Snapdragon hardware using the included profiling script:
```bash
python docs/aihub_profile.py
```

---

## Quick Start

### 1. Prerequisites
- **Python:** 3.11, 3.12, or 3.13
- **Operating System:** Windows 10/11, macOS, or Linux
- **FFmpeg:** Bundled automatically via `imageio-ffmpeg` (no external installation required)

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/GoDxVictoryRR/snapvid.git
cd snapvid

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```

Open `.env` and set your preferred LLM endpoint. For Ollama:
```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
LLM_API_KEY=
LLM_TIMEOUT=120
TTS_ENGINE=auto
```

*(Note: You can also configure all provider settings, models, and API keys directly inside the web studio UI without editing `.env`.)*

### 4. Running SnapVid

#### Mode A: Interactive Web Studio (Recommended)
```bash
python -m snapvid.server
# or: python -m snapreel.server
```
Visit **`http://localhost:8000`** in your browser.

#### Mode B: Command-Line Interface (CLI)
Generate an explainer video directly from your terminal:
```bash
python run.py "Explain how photosynthesis converts sunlight into glucose"
```
The finished video will be compiled to `output/explain_how_photosynthesis_<timestamp>.mp4`.

---

## Python API Usage

Embed SnapVid directly into your automated pipelines, bots, or research workflows:

```python
from snapreel.planner import generate
from snapreel.renderer import render_video

# 1. Plan and validate scene script using agentic loop
script = generate(
    topic="How Large Language Models Use Attention Mechanisms",
    target_duration=60,
    aspect_ratio="16:9"
)

# 2. Render synchronized video with audio & captions
output_path = "output/attention_mechanisms.mp4"
render_video(script, output_path)

print(f"Video created successfully at: {output_path}")
```

---

## Repository Structure

```
snapvid/
├── snapreel/                  # Core video generation engine
│   ├── llm.py                 # Unified LLM caller with retry & SSE streaming
│   ├── planner.py             # Agentic scene planner & self-healing loop
│   ├── quality.py             # Quality critic agent pass
│   ├── schema.py              # Pydantic v2 scene specifications & validator
│   ├── renderer.py            # Pillow/NumPy frame compositor & FFmpeg pipeline
│   ├── transitions.py         # Fade, Slide, Zoom, and Dissolve transition blender
│   ├── tts.py                 # Kokoro, Edge TTS, SAPI engine & duration reconciler
│   ├── server.py              # FastAPI server with SSE events & REST endpoints
│   ├── history.py             # Generation history persistence
│   ├── npu.py                 # Snapdragon NPU detection & benchmark logger
│   └── templates/             # 10 Animated visual templates
│       ├── title.py           # Title & hero intro cards
│       ├── bullets.py         # Sequential bullet points
│       ├── bar_chart.py       # Comparative animated charts
│       ├── counter.py         # Eased metric counters
│       ├── code_block.py      # Syntax-highlighted code container
│       ├── kinetic.py         # High-impact kinetic typography
│       ├── lower_third.py     # Informational bottom banners
│       ├── quote.py           # Testimonial and quote cards
│       ├── icon_list.py       # Glyphed feature pill list
│       └── split.py           # Dual-column side-by-side cards
├── snapvid/                   # Package entry-point aliases
│   ├── __init__.py            # Clean module exports
│   └── server.py              # Web server runner
├── ui/                        # Studio interface (Vanilla HTML5 / CSS3 / JS)
│   ├── index.html             # Modern studio dashboard
│   ├── style.css              # Dark glassmorphism & responsive layout
│   └── app.js                 # SSE consumer, history manager & settings logic
├── tests/                     # Comprehensive automated test suite (74 tests)
├── docs/                      # Technical documentation & NPU profiling tools
├── scripts/                   # Pitch decks & project description generators
├── run.py                     # Headless CLI entry point
├── requirements.txt           # Python dependency specifications
├── LICENSE                    # MIT License
└── README.md                  # Project documentation
```

---

## Test Suite & Quality Verification

SnapVid includes an automated test suite with **74 tests** covering schema integrity, LLM fallback behavior, template frame calculations, transition blends, TTS audio generation, duration reconciliation, and HTTP endpoints:

```bash
python -m pytest tests/ -v
```

```
============================= test session starts =============================
collected 74 items

tests/test_schema.py ...............                                    [ 20%]
tests/test_llm.py .........                                             [ 32%]
tests/test_planner.py ...                                               [ 36%]
tests/test_quality.py ....                                              [ 41%]
tests/test_renderer.py ............                                     [ 58%]
tests/test_transitions.py ...                                           [ 62%]
tests/test_tts.py ...............                                       [ 82%]
tests/test_server.py .........                                          [ 94%]
tests/test_npu.py ....                                                  [100%]

============================= 74 passed in 58.90s =============================
```

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for complete details.
