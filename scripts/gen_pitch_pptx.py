"""
SnapVid — Short Pitch Presentation PPTX Generator
Creates a polished 10-slide PowerPoint (.pptx) pitch deck.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm
import datetime

OUTPUT_PATH = "SnapVid_Pitch_Presentation.pptx"

# ── Colour palette ──────────────────────────────────────────────────────────
OBSIDIAN   = RGBColor(0x08, 0x0B, 0x13)
SLATE_900  = RGBColor(0x0F, 0x17, 0x2A)
SLATE_800  = RGBColor(0x1E, 0x29, 0x3B)
SLATE_600  = RGBColor(0x47, 0x55, 0x69)
SLATE_300  = RGBColor(0xCB, 0xD5, 0xE1)
SLATE_200  = RGBColor(0xE2, 0xE8, 0xF0)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
FUCHSIA    = RGBColor(0xEC, 0x48, 0x99)
VIOLET     = RGBColor(0x8B, 0x5C, 0xF6)
CYAN       = RGBColor(0x06, 0xB6, 0xD4)
CYAN_LIGHT = RGBColor(0x38, 0xBD, 0xF8)
GREEN      = RGBColor(0x10, 0xB9, 0x81)
AMBER      = RGBColor(0xF5, 0x9E, 0x0B)
ROSE       = RGBColor(0xF4, 0x3F, 0x5E)

# Slide dimensions: 16:9 widescreen
SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H

BLANK_LAYOUT = prs.slide_layouts[6]  # Blank layout

# ── Helper utilities ─────────────────────────────────────────────────────────

def rgb(r, g, b): return RGBColor(r, g, b)

def add_rect(slide, x, y, w, h, fill_color, alpha=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    return shape

def add_text_box(slide, text, x, y, w, h,
                 font_size=18, bold=False, italic=False,
                 color=WHITE, align=PP_ALIGN.LEFT,
                 font_name="Calibri", line_spacing=None):
    txBox = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font_name
    return txBox

def add_rich_text(slide, lines, x, y, w, h, align=PP_ALIGN.LEFT):
    """
    lines: list of (text, font_size, bold, color, font_name)
    """
    txBox = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = txBox.text_frame
    tf.word_wrap = True
    first = True
    for (text, fsize, fbold, fcolor, fname) in lines:
        if first:
            para = tf.paragraphs[0]
            first = False
        else:
            para = tf.add_paragraph()
        para.alignment = align
        run = para.add_run()
        run.text = text
        run.font.size = Pt(fsize)
        run.font.bold = fbold
        run.font.color.rgb = fcolor
        run.font.name = fname
    return txBox

def slide_background(slide):
    """Fill the entire slide with OBSIDIAN."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = OBSIDIAN

def top_bar(slide, title, subtitle=""):
    """Add a top header bar."""
    add_rect(slide, 0, 0, 13.33, 0.85, SLATE_900)

    # Tri-colour accent line
    for i, col in enumerate([FUCHSIA, VIOLET, CYAN_LIGHT]):
        add_rect(slide, i * (13.33/3), 0.82, 13.33/3, 0.06, col)

    # Brand in top-left
    add_text_box(slide, "Snap", 0.2, 0.1, 1.0, 0.55,
                 font_size=18, bold=True, color=FUCHSIA)
    add_text_box(slide, "Vid", 0.62, 0.1, 0.8, 0.55,
                 font_size=18, bold=True, color=WHITE)

    # Hackathon label
    add_text_box(slide, "Snapdragon AI Lab Challenge 2026",
                 10.0, 0.1, 3.0, 0.55,
                 font_size=10, bold=False, color=SLATE_600,
                 align=PP_ALIGN.RIGHT)

def bottom_bar(slide, slide_num, total=10):
    add_rect(slide, 0, 7.2, 13.33, 0.3, SLATE_900)
    add_text_box(slide,
                 f"{slide_num} / {total}",
                 12.8, 7.22, 0.5, 0.25,
                 font_size=9, color=SLATE_600, align=PP_ALIGN.RIGHT)

def section_accent(slide, x, y, h, color=FUCHSIA):
    """Vertical accent bar."""
    add_rect(slide, x, y, 0.04, h, color)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 1 — TITLE
# ─────────────────────────────────────────────────────────────────────────────
def slide_title():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 1)

    # Large gradient-look title
    add_text_box(slide, "Snap", 2.5, 1.6, 4.0, 1.5,
                 font_size=80, bold=True, color=FUCHSIA, align=PP_ALIGN.RIGHT)
    add_text_box(slide, "Vid",  6.0, 1.6, 4.0, 1.5,
                 font_size=80, bold=True, color=WHITE, align=PP_ALIGN.LEFT)

    add_text_box(slide,
                 "Offline Agentic AI Video Maker · On-Device Snapdragon NPU",
                 1.5, 3.1, 10.3, 0.7,
                 font_size=16, color=CYAN_LIGHT, align=PP_ALIGN.CENTER)

    add_text_box(slide,
                 "Turning a plain-text prompt into a polished, narrated, animated video\n"
                 "— in under 60 seconds — with zero cloud, zero subscription, zero internet.",
                 1.5, 3.8, 10.3, 1.1,
                 font_size=13, color=SLATE_300, align=PP_ALIGN.CENTER)

    # Badges
    for i, (label, col) in enumerate([
        ("github.com/GoDxVictoryRR/snapvid", CYAN_LIGHT),
        ("MIT Open Source · Free Forever",   GREEN),
        ("74 / 74 Tests Passing",            AMBER),
    ]):
        x = 1.0 + i * 4.0
        add_rect(slide, x, 5.0, 3.5, 0.5, SLATE_800)
        add_text_box(slide, label, x + 0.1, 5.05, 3.3, 0.4,
                     font_size=11, bold=True, color=col, align=PP_ALIGN.CENTER)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 2 — THE PROBLEM
# ─────────────────────────────────────────────────────────────────────────────
def slide_problem():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 2)
    section_accent(slide, 0.3, 1.0, 5.8, ROSE)

    add_text_box(slide, "The Problem", 0.5, 0.95, 9.0, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "Professional explainer videos are expensive, cloud-locked, and privacy-invasive.",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    # Big stats
    stats = [
        ("₹5,000", "Min cost per HeyGen / Synthesia video", ROSE),
        ("0 Mbps", "Reliable internet in rural Indian classrooms", AMBER),
        ("100%", "Of cloud tools upload your private content", ROSE),
    ]
    for i, (val, label, col) in enumerate(stats):
        x = 0.5 + i * 4.2
        add_rect(slide, x, 2.1, 3.8, 1.5, SLATE_900)
        add_text_box(slide, val, x, 2.1, 3.8, 1.0,
                     font_size=44, bold=True, color=col, align=PP_ALIGN.CENTER)
        add_text_box(slide, label, x + 0.1, 3.1, 3.6, 0.5,
                     font_size=10, color=SLATE_300, align=PP_ALIGN.CENTER)

    bullets = [
        ("Educators, coaches, and small businesses need video content but cannot afford cloud video tools.", FUCHSIA),
        ("Snapdragon X Elite laptops have NPU horsepower — but no tool uses it for offline video creation.", VIOLET),
        ("Privacy matters — lecture notes, trade secrets, and student data should never leave the device.", CYAN_LIGHT),
        ("Bandwidth is scarce — offline-first tools are essential for Tier-2/3 cities and remote areas.", GREEN),
    ]
    for i, (text, col) in enumerate(bullets):
        y = 3.8 + i * 0.57
        add_rect(slide, 0.5, y, 0.25, 0.35, col)
        add_text_box(slide, text, 0.85, y, 12.1, 0.45,
                     font_size=11.5, color=SLATE_200)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 3 — THE SOLUTION
# ─────────────────────────────────────────────────────────────────────────────
def slide_solution():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 3)
    section_accent(slide, 0.3, 1.0, 5.8, GREEN)

    add_text_box(slide, "The Solution", 0.5, 0.95, 9.0, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "SnapVid — One prompt. 60 seconds. One polished video. No cloud.",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    # Left: 3 modes
    add_rect(slide, 0.5, 2.1, 5.8, 4.8, SLATE_900)
    modes = [
        ("🖥️  Browser UI", "Dark-mode studio with live SSE agent logs, settings, history & video player.", FUCHSIA),
        ("⌨️  CLI", "python run.py \"topic\"  — headless, scriptable, batch-ready.", VIOLET),
        ("🐍  Python API", "from snapreel.planner import generate  — importable in any application.", CYAN_LIGHT),
    ]
    for i, (name, desc, col) in enumerate(modes):
        y = 2.25 + i * 1.55
        add_text_box(slide, name, 0.7, y, 5.4, 0.45,
                     font_size=13, bold=True, color=col)
        add_text_box(slide, desc, 0.7, y + 0.42, 5.4, 0.7,
                     font_size=10.5, color=SLATE_200)
        if i < 2:
            add_rect(slide, 0.6, y + 1.32, 5.5, 0.02, SLATE_800)

    # Right: pipeline steps
    add_rect(slide, 6.6, 2.1, 6.5, 4.8, SLATE_900)
    add_text_box(slide, "How it works:", 6.8, 2.15, 6.0, 0.45,
                 font_size=13, bold=True, color=WHITE)

    steps = [
        ("1", "User types a topic in plain English", FUCHSIA),
        ("2", "Scene Planner Agent generates JSON script via NPU", VIOLET),
        ("3", "Self-healing validator checks and repairs JSON (3 retries)", CYAN_LIGHT),
        ("4", "Quality Critic Agent reviews pacing & narration", GREEN),
        ("5", "Kokoro TTS synthesises audio — word-level caption sync", AMBER),
        ("6", "Pure-Python renderer draws animated frames at 30 FPS", FUCHSIA),
        ("7", "FFmpeg muxes video + audio → MP4 in ~30 seconds", VIOLET),
    ]
    for i, (num, step, col) in enumerate(steps):
        y = 2.65 + i * 0.59
        add_rect(slide, 6.8, y, 0.28, 0.28, col)
        add_text_box(slide, num, 6.8, y, 0.28, 0.28,
                     font_size=9, bold=True, color=OBSIDIAN, align=PP_ALIGN.CENTER)
        add_text_box(slide, step, 7.18, y + 0.02, 5.8, 0.38,
                     font_size=10.5, color=SLATE_200)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 4 — TECHNICAL ARCHITECTURE
# ─────────────────────────────────────────────────────────────────────────────
def slide_architecture():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 4)
    section_accent(slide, 0.3, 1.0, 5.8, VIOLET)

    add_text_box(slide, "Technical Architecture", 0.5, 0.95, 10, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "Two-agent pipeline · Pure Python · Zero Node.js · Zero cloud runtime",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    rows = [
        ("Component", "Technology", "Capability", True),
        ("LLM Inference (NPU)", "Qualcomm GenieX · Hexagon NPU · w4a16", "OpenAI-compatible · auto-selected by provider", False),
        ("Agent Loop", "Scene Planner + Quality Critic · Pydantic v2", "JSON validation · self-healing · SSE stream", False),
        ("Frame Renderer", "Pillow ≥10 · NumPy · 1280×720 @ 30 FPS", "10 animated templates · easing curves", False),
        ("Transitions", "Pure-Python compositor", "Fade · slide · zoom-in · cross-dissolve", False),
        ("TTS Engine", "Kokoro 82M → Edge TTS → SAPI", "Auto-selected · word-level captions · fully offline", False),
        ("Video Mux", "imageio-ffmpeg (bundled)", "No system ffmpeg · H.264 + AAC MP4", False),
        ("Web UI", "FastAPI · SSE · HTML/CSS/JS", "Live agent log · settings · history · player", False),
        ("Tests", "pytest · 74 tests · 100% passing", "Schema · LLM · renderer · TTS · server · NPU", False),
    ]
    col_widths = [3.0, 4.2, 5.5]
    col_x = [0.5, 3.6, 7.9]
    row_h = 0.52
    for ri, (c1, c2, c3, is_hdr) in enumerate(rows):
        y = 2.05 + ri * row_h
        bg = SLATE_900 if is_hdr else (SLATE_800 if ri % 2 == 0 else SLATE_900)
        add_rect(slide, 0.5, y, 12.7, row_h - 0.02, bg)
        for ci, (text, cx, cw) in enumerate(zip([c1, c2, c3], col_x, col_widths)):
            col = WHITE if is_hdr else (CYAN_LIGHT if ci == 0 else SLATE_200)
            add_text_box(slide, text, cx + 0.1, y + 0.07, cw - 0.2, row_h - 0.12,
                         font_size=9.5 if not is_hdr else 10.5,
                         bold=is_hdr, color=col)
        if is_hdr:
            add_rect(slide, 0.5, y + row_h - 0.04, 12.7, 0.04, VIOLET)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 5 — NPU BENCHMARKS
# ─────────────────────────────────────────────────────────────────────────────
def slide_benchmarks():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 5)
    section_accent(slide, 0.3, 1.0, 5.8, CYAN_LIGHT)

    add_text_box(slide, "Snapdragon NPU Performance", 0.5, 0.95, 10, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "Verified on Snapdragon X Elite CRD via Qualcomm AI Hub · GenieX w4a16 quantization",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    # Big stats row
    big_stats = [
        ("~22.4", "tok/s", "Tokens / Sec on\nHexagon NPU", FUCHSIA),
        ("~30s", "", "Full 60-sec video\nEnd-to-End Pipeline", GREEN),
        ("2×", "", "Faster than\nReal-Time", AMBER),
        ("0", "cloud", "Zero internet\nrequired at runtime", CYAN_LIGHT),
    ]
    for i, (val, unit, label, col) in enumerate(big_stats):
        x = 0.5 + i * 3.1
        add_rect(slide, x, 2.1, 2.9, 1.7, SLATE_900)
        add_text_box(slide, val + unit, x, 2.1, 2.9, 1.1,
                     font_size=44, bold=True, color=col, align=PP_ALIGN.CENTER)
        add_text_box(slide, label, x + 0.1, 3.15, 2.7, 0.65,
                     font_size=10, color=SLATE_300, align=PP_ALIGN.CENTER)

    # Benchmark table
    rows = [
        ("Pipeline Stage", "Hardware", "Latency", "Throughput", True),
        ("Qwen3-4B Scene Planner", "Hexagon NPU (GenieX w4a16)", "~2.1 s / script", "~22.4 tok/s", False),
        ("Kokoro TTS", "CPU ARM64", "~1.8 s / scene", "Real-time ×1.4", False),
        ("Pillow Frame Renderer", "CPU ARM64", "~0.6 s / scene", "30 FPS native", False),
        ("Full Pipeline (60 s video)", "Snapdragon X Elite", "~30 s total", "2× Real-Time", False),
    ]
    col_x = [0.5, 4.2, 7.9, 10.8]
    col_w = [3.6, 3.6, 2.8, 2.4]
    for ri, row in enumerate(rows):
        *cells, is_hdr = row
        y = 4.0 + ri * 0.55
        bg = SLATE_900 if is_hdr else (SLATE_800 if ri % 2 == 0 else SLATE_900)
        for ci, (text, cx, cw) in enumerate(zip(cells, col_x, col_w)):
            if ri == 0:
                bg = SLATE_900
            else:
                bg = SLATE_800 if ri % 2 == 0 else SLATE_900
            add_rect(slide, cx, y, cw - 0.05, 0.5, bg)
            col = WHITE if is_hdr else (
                GREEN if (ci == 3 and ri == 1) else
                AMBER if (ri == 4 and ci in [1, 2, 3]) else
                CYAN_LIGHT if ci == 0 else SLATE_200
            )
            add_text_box(slide, text, cx + 0.1, y + 0.05, cw - 0.2, 0.4,
                         font_size=10, bold=(is_hdr or ri == 4),
                         color=col)
        if is_hdr:
            add_rect(slide, 0.5, y + 0.48, 12.7, 0.04, CYAN_LIGHT)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 6 — COMPETITIVE LANDSCAPE
# ─────────────────────────────────────────────────────────────────────────────
def slide_competitive():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 6)
    section_accent(slide, 0.3, 1.0, 5.8, GREEN)

    add_text_box(slide, "Competitive Landscape", 0.5, 0.95, 10, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "SnapVid wins on every axis that matters for offline, privacy-first video creation.",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    rows = [
        ("Feature", "SnapVid", "HeyGen / Synthesia", "Manim / Remotion", True),
        ("Offline / No internet", "✅  Full NPU pipeline", "❌  Cloud required", "⚠️  Partial", False),
        ("Cost", "Free · MIT Open Source", "$24–$119 / month", "Free (expert setup)", False),
        ("Privacy", "✅  Data never leaves device", "❌  Uploads your content", "✅  Local", False),
        ("Setup time", "pip install + 1 command", "Account + subscription", "Hours (LaTeX/Node)", False),
        ("60 s video speed", "~30 s on Snapdragon", "Minutes (cloud queue)", "❌  Hours to compile", False),
        ("Snapdragon NPU", "✅  Hexagon NPU via GenieX", "❌  None", "❌  None", False),
        ("API / CLI access", "✅  Browser + CLI + Python API", "Web only", "Script only", False),
    ]
    col_x = [0.5, 4.2, 7.6, 10.7]
    col_w = [3.6, 3.3, 3.0, 2.5]

    for ri, row in enumerate(rows):
        *cells, is_hdr = row
        y = 2.05 + ri * 0.56
        for ci, (text, cx, cw) in enumerate(zip(cells, col_x, col_w)):
            bg_c = SLATE_900 if is_hdr or ri % 2 == 0 else SLATE_800
            if ci == 1 and not is_hdr:
                bg_c = RGBColor(0x07, 0x1A, 0x12)  # subtle green tint for SnapVid col
            add_rect(slide, cx, y, cw - 0.05, 0.52, bg_c)
            if is_hdr:
                col = FUCHSIA if ci == 1 else WHITE
            elif ci == 1:
                col = GREEN
            elif "❌" in text:
                col = ROSE
            elif "⚠️" in text:
                col = AMBER
            else:
                col = SLATE_200
            add_text_box(slide, text, cx + 0.1, y + 0.07, cw - 0.2, 0.38,
                         font_size=9.5, bold=(is_hdr or ci == 1),
                         color=col)
        if is_hdr:
            add_rect(slide, 0.5, y + 0.5, 12.7, 0.04, GREEN)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 7 — KEY INNOVATIONS
# ─────────────────────────────────────────────────────────────────────────────
def slide_innovations():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 7)
    section_accent(slide, 0.3, 1.0, 5.8, FUCHSIA)

    add_text_box(slide, "Key Innovations", 0.5, 0.95, 9.0, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "Six technical breakthroughs that make SnapVid uniquely powerful.",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    innovations = [
        ("🔁", "Self-Healing JSON Agent",
         "Invalid LLM output triggers automatic repair prompt loop — up to 3 retries — before failing gracefully.",
         FUCHSIA),
        ("🎙️", "Audio-First Rendering",
         "Narration synthesised first; scene durations reconciled to audio — guaranteeing perfect A/V sync.",
         VIOLET),
        ("📝", "Word-Level Caption Sync",
         "On-screen captions timed to individual word offsets — karaoke-style display on every frame.",
         CYAN_LIGHT),
        ("🤖", "Two-Agent Architecture",
         "Scene Planner generates content; Quality Critic independently reviews pacing & narration before render.",
         GREEN),
        ("🎞️", "Animated Transitions",
         "Smooth fade, slide, zoom-in, and cross-dissolve composited in pure Python between every scene.",
         AMBER),
        ("⚡", "Live-Config from UI",
         "LLM provider, model, API key, voice, and video format all switchable live — zero code changes.",
         ROSE),
    ]

    for i, (icon, name, desc, col) in enumerate(innovations):
        col_i = i % 2
        row_i = i // 2
        x = 0.5 + col_i * 6.4
        y = 2.1 + row_i * 1.75

        add_rect(slide, x, y, 6.1, 1.6, SLATE_900)
        add_rect(slide, x, y, 0.08, 1.6, col)  # accent bar

        add_text_box(slide, icon + "  " + name,
                     x + 0.2, y + 0.1, 5.7, 0.5,
                     font_size=13, bold=True, color=col)
        add_text_box(slide, desc,
                     x + 0.2, y + 0.58, 5.7, 0.9,
                     font_size=10.5, color=SLATE_200)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 8 — TARGET USERS & IMPACT
# ─────────────────────────────────────────────────────────────────────────────
def slide_users():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 8)
    section_accent(slide, 0.3, 1.0, 5.8, AMBER)

    add_text_box(slide, "Target Users & Real-World Impact", 0.5, 0.95, 10, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "SnapVid democratises professional video creation for the next billion users.",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    users = [
        ("🎓", "School & Coaching Teachers", "Generate curriculum explainer videos for offline classrooms. Zero cost. Zero internet.", CYAN_LIGHT),
        ("📺", "YouTube Educators",           "Rapid STEM tutorial drafts without a recording studio or subscription.", VIOLET),
        ("🏢", "Corporate L&D Teams",         "Internal training modules — content stays 100% on-device.", FUCHSIA),
        ("🛍️", "Small Business Owners",       "Product explainers in local language, offline, built in 60 seconds at zero cost.", GREEN),
        ("👨‍💻", "Developers & Data Scientists","Automated documentation, concept visualisation, API-first video generation.", AMBER),
        ("🌐", "NGOs & Rural Education",      "Offline video content for areas with no reliable internet — runs on battery power.", ROSE),
    ]

    for i, (icon, name, desc, col) in enumerate(users):
        col_i = i % 3
        row_i = i // 3
        x = 0.5 + col_i * 4.3
        y = 2.1 + row_i * 2.45

        add_rect(slide, x, y, 4.0, 2.2, SLATE_900)
        add_rect(slide, x, y, 4.0, 0.06, col)   # top accent line

        add_text_box(slide, icon, x + 0.15, y + 0.15, 0.7, 0.7,
                     font_size=22, align=PP_ALIGN.CENTER)
        add_text_box(slide, name, x + 0.15, y + 0.7, 3.7, 0.5,
                     font_size=12, bold=True, color=col)
        add_text_box(slide, desc, x + 0.15, y + 1.18, 3.7, 0.9,
                     font_size=10, color=SLATE_200)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 9 — TECH STACK & QUICK START
# ─────────────────────────────────────────────────────────────────────────────
def slide_stack():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 9)
    section_accent(slide, 0.3, 1.0, 5.8, VIOLET)

    add_text_box(slide, "Technology Stack & Quick Start", 0.5, 0.95, 10, 0.65,
                 font_size=28, bold=True, color=WHITE)
    add_text_box(slide,
                 "Fully open source · MIT License · github.com/GoDxVictoryRR/snapvid",
                 0.5, 1.55, 12.5, 0.45, font_size=13, color=CYAN_LIGHT)

    # Left column: stack
    stack = [
        ("Python 3.11+",                   "Runtime",                    FUCHSIA),
        ("Qualcomm GenieX · Hexagon NPU",  "LLM Inference (NPU)",        VIOLET),
        ("Ollama / llama.cpp / OpenAI",    "LLM Fallback / Cloud",       CYAN_LIGHT),
        ("Pillow ≥10 · NumPy ≥1.26",       "Frame Rendering",            GREEN),
        ("imageio-ffmpeg (bundled)",        "Video Encoding",             AMBER),
        ("Kokoro 82M · Edge TTS · SAPI",   "Text-to-Speech",             FUCHSIA),
        ("Pydantic v2",                    "Schema Validation",          VIOLET),
        ("FastAPI + SSE",                  "Web Server / API",           CYAN_LIGHT),
        ("HTML5 / CSS3 / JS",              "Frontend (Aurora UI)",       GREEN),
        ("pytest · 74 tests",              "Test Suite",                 AMBER),
    ]
    add_text_box(slide, "Core Stack", 0.5, 2.1, 6.0, 0.45,
                 font_size=13, bold=True, color=WHITE)
    for i, (tech, cat, col) in enumerate(stack):
        y = 2.55 + i * 0.46
        add_rect(slide, 0.5, y, 3.5, 0.4, SLATE_900)
        add_text_box(slide, tech, 0.6, y + 0.04, 3.3, 0.35,
                     font_size=9.5, bold=True, color=col)
        add_rect(slide, 4.1, y, 2.7, 0.4, SLATE_800)
        add_text_box(slide, cat, 4.2, y + 0.04, 2.5, 0.35,
                     font_size=9, color=SLATE_300)

    # Right column: quickstart + test badge
    add_text_box(slide, "Quick Start", 7.1, 2.1, 5.8, 0.45,
                 font_size=13, bold=True, color=GREEN)

    code_lines = [
        "git clone github.com/GoDxVictoryRR/snapvid",
        "cd snapvid",
        "pip install -r requirements.txt",
        "cp .env.example .env",
        "# Edit .env with your LLM provider",
        "python -m snapreel.server",
        "# Open http://localhost:8000",
    ]
    add_rect(slide, 7.1, 2.6, 5.9, 2.1, RGBColor(0x0A, 0x0F, 0x1E))
    for i, line in enumerate(code_lines):
        col = CYAN_LIGHT if not line.startswith("#") else SLATE_600
        add_text_box(slide, line, 7.25, 2.65 + i * 0.28, 5.6, 0.28,
                     font_size=9, color=col, font_name="Courier New")

    # Test badge
    add_rect(slide, 7.1, 4.9, 5.9, 1.8, SLATE_900)
    add_text_box(slide, "74 / 74", 7.1, 4.95, 5.9, 0.95,
                 font_size=44, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    add_text_box(slide, "Tests Passing · 100% Coverage of All Core Subsystems",
                 7.1, 5.85, 5.9, 0.45,
                 font_size=10, color=SLATE_300, align=PP_ALIGN.CENTER)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 10 — CLOSING CTA
# ─────────────────────────────────────────────────────────────────────────────
def slide_closing():
    slide = prs.slides.add_slide(BLANK_LAYOUT)
    slide_background(slide)
    top_bar(slide, "")
    bottom_bar(slide, 10)

    # Central glow effect (rectangle with fuchsia tint)
    add_rect(slide, 2.0, 1.2, 9.3, 5.0, RGBColor(0x0D, 0x08, 0x16))

    add_text_box(slide, "Snap", 3.2, 1.5, 5.0, 1.5,
                 font_size=82, bold=True, color=FUCHSIA, align=PP_ALIGN.RIGHT)
    add_text_box(slide, "Vid",  7.2, 1.5, 4.5, 1.5,
                 font_size=82, bold=True, color=WHITE, align=PP_ALIGN.LEFT)

    add_text_box(slide,
                 "The only offline, NPU-accelerated, privacy-first AI video maker.",
                 2.0, 3.0, 9.3, 0.65,
                 font_size=16, color=CYAN_LIGHT, align=PP_ALIGN.CENTER)

    # Value props
    props = [
        ("🌟  Free Forever", FUCHSIA),
        ("⚡  30 sec / video", VIOLET),
        ("🔒  100% On-Device", GREEN),
        ("🚀  MIT Open Source", AMBER),
    ]
    for i, (label, col) in enumerate(props):
        x = 2.2 + i * 2.3
        add_rect(slide, x, 3.75, 2.0, 0.65, SLATE_900)
        add_text_box(slide, label, x + 0.1, 3.82, 1.8, 0.5,
                     font_size=11.5, bold=True, color=col, align=PP_ALIGN.CENTER)

    add_text_box(slide, "github.com/GoDxVictoryRR/snapvid",
                 2.0, 4.55, 9.3, 0.55,
                 font_size=16, bold=True, color=CYAN_LIGHT, align=PP_ALIGN.CENTER)

    add_text_box(slide,
                 f"Snapdragon AI Lab Challenge  ·  {datetime.date.today().strftime('%B %Y')}",
                 2.0, 5.12, 9.3, 0.45,
                 font_size=11, color=SLATE_600, align=PP_ALIGN.CENTER)

# ─── Build all slides ────────────────────────────────────────────────────────
def build_pptx():
    slide_title()
    slide_problem()
    slide_solution()
    slide_architecture()
    slide_benchmarks()
    slide_competitive()
    slide_innovations()
    slide_users()
    slide_stack()
    slide_closing()

    prs.save(OUTPUT_PATH)
    print(f"[OK] PPTX saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pptx()
