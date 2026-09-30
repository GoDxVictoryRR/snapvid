"""
SnapVid — Brief Project Description Generator
Produces a professional 1-page PDF brief.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import datetime

OUTPUT_PATH = "SnapVid_Brief_Project_Description.pdf"

# ── Colour palette ──────────────────────────────────────────────────────────
OBSIDIAN   = colors.HexColor("#080B13")
FUCHSIA    = colors.HexColor("#EC4899")
VIOLET     = colors.HexColor("#8B5CF6")
CYAN_LIGHT = colors.HexColor("#38BDF8")
SLATE_900  = colors.HexColor("#0F172A")
SLATE_700  = colors.HexColor("#334155")
SLATE_400  = colors.HexColor("#94A3B8")
SLATE_200  = colors.HexColor("#E2E8F0")
WHITE      = colors.white
GREEN      = colors.HexColor("#10B981")
AMBER      = colors.HexColor("#F59E0B")

PAGE_W, PAGE_H = A4  # 210 × 297 mm

def build_brief():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm,  bottomMargin=16*mm,
        title="SnapVid — Brief Project Description",
        author="GoDxVictoryRR / SnapVid Team",
    )

    styles = getSampleStyleSheet()

    # ── Custom paragraph styles ──────────────────────────────────────────────
    h1 = ParagraphStyle("H1", parent=styles["Normal"],
        fontSize=26, leading=30, fontName="Helvetica-Bold",
        textColor=WHITE, spaceAfter=2)
    h1_sub = ParagraphStyle("H1Sub", parent=styles["Normal"],
        fontSize=11, leading=14, fontName="Helvetica",
        textColor=CYAN_LIGHT, spaceAfter=0)
    section_head = ParagraphStyle("SH", parent=styles["Normal"],
        fontSize=10, leading=13, fontName="Helvetica-Bold",
        textColor=FUCHSIA, spaceBefore=10, spaceAfter=4,
        borderPad=0)
    body = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9.5, leading=14.5, fontName="Helvetica",
        textColor=SLATE_200, alignment=TA_JUSTIFY, spaceAfter=4)
    bullet = ParagraphStyle("Bullet", parent=styles["Normal"],
        fontSize=9, leading=13.5, fontName="Helvetica",
        textColor=SLATE_200, leftIndent=12, firstLineIndent=0,
        spaceAfter=2)
    table_cell = ParagraphStyle("TC", parent=styles["Normal"],
        fontSize=8.5, leading=12, fontName="Helvetica",
        textColor=SLATE_200)
    table_head = ParagraphStyle("TH", parent=styles["Normal"],
        fontSize=8.5, leading=12, fontName="Helvetica-Bold",
        textColor=WHITE)
    tag_style = ParagraphStyle("Tag", parent=styles["Normal"],
        fontSize=8, leading=11, fontName="Helvetica-Bold",
        textColor=OBSIDIAN)
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"],
        fontSize=7.5, leading=11, fontName="Helvetica",
        textColor=SLATE_400, alignment=TA_CENTER)

    # ── Helper: gradient header block ───────────────────────────────────────
    def header_block():
        # We'll use a Table to fake a coloured header strip
        logo_txt = Paragraph(
            '<font color="#EC4899"><b>Snap</b></font>'
            '<font color="#FFFFFF"><b>Vid</b></font>', 
            ParagraphStyle("Logo", parent=styles["Normal"],
                fontSize=28, leading=32, fontName="Helvetica-Bold")
        )
        tagline = Paragraph(
            "Agentic AI Video Maker · Offline · On-Device NPU · Pure Python", h1_sub)
        date_txt = Paragraph(
            f"Project Brief  ·  {datetime.date.today().strftime('%B %Y')}",
            ParagraphStyle("Date", parent=styles["Normal"],
                fontSize=8, fontName="Helvetica", textColor=SLATE_400,
                alignment=TA_CENTER)
        )

        inner = Table(
            [[logo_txt, tagline]],
            colWidths=[55*mm, None]
        )
        inner.setStyle(TableStyle([
            ("VALIGN",    (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING",(0,0),(-1,-1), 0),
        ]))

        outer = Table(
            [[inner], [date_txt]],
            colWidths=[PAGE_W - 36*mm]
        )
        outer.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), SLATE_900),
            ("BACKGROUND", (0,1), (-1,1), OBSIDIAN),
            ("TOPPADDING",    (0,0), (-1,0), 12),
            ("BOTTOMPADDING", (0,0), (-1,0), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
            ("TOPPADDING",    (0,1), (-1,1), 4),
            ("BOTTOMPADDING", (0,1), (-1,1), 6),
            ("LINEBELOW", (0,0), (-1,0), 2, FUCHSIA),
        ]))
        return outer

    def section(title, content_flowables):
        """Returns a list of flowables for a titled section."""
        return [
            Paragraph(f"▸  {title}", section_head),
            HRFlowable(width="100%", thickness=0.5, color=VIOLET,
                       spaceAfter=5, spaceBefore=0, dash=None),
        ] + content_flowables

    def bullet_item(text):
        return Paragraph(f"<bullet>&bull;</bullet> {text}", bullet)

    def badge(text, bg_color=VIOLET, fg=WHITE):
        t = Table([[Paragraph(f"<b>{text}</b>",
                    ParagraphStyle("B", parent=styles["Normal"],
                        fontSize=7.5, leading=10, fontName="Helvetica-Bold",
                        textColor=fg)
                   )]], colWidths=[None])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), bg_color),
            ("ROUNDEDCORNERS",[3]),
            ("TOPPADDING",    (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ]))
        return t

    # ─────────────────────────────────────────────────────────────────────────
    story = []

    # Header
    story.append(header_block())
    story.append(Spacer(1, 6*mm))

    # ── 1. PROBLEM STATEMENT ─────────────────────────────────────────────────
    story += section("Problem Statement", [
        Paragraph(
            "Creating professional explainer videos is expensive, slow, and cloud-dependent. "
            "Tools like HeyGen or Synthesia cost <b>₹5,000–₹50,000 per video</b> and require "
            "uploading private content to the internet. For educators, coaches, and small "
            "businesses in low-bandwidth environments — this is a hard wall.", body),
        Paragraph(
            "Meanwhile, modern AI-capable Snapdragon X Elite laptops possess <b>enough on-device "
            "NPU compute</b> to run language models at 22+ tokens/second — yet no tool exists "
            "that turns this power into ready-to-share video content, fully offline.", body),
    ])

    story.append(Spacer(1, 3*mm))

    # ── 2. SOLUTION ──────────────────────────────────────────────────────────
    story += section("Solution — SnapVid", [
        Paragraph(
            "<b>SnapVid</b> is an <b>offline, agentic AI explainer-video maker</b> that runs "
            "entirely on a Snapdragon X Elite laptop — no cloud, no subscriptions, no internet. "
            "It converts a single plain-text prompt into a <b>polished, narrated, animated MP4 "
            "video in under 60 seconds</b> using a two-agent pipeline.", body),
        Spacer(1, 2*mm),
        Paragraph("Three deployment modes — all without leaving the device:", body),
        bullet_item("<b>Browser UI</b>  —  Dark-mode studio dashboard with live SSE agent logs, settings modal, history, and built-in video player."),
        bullet_item("<b>CLI</b>  —  <i>python run.py \"your topic\"</i>  for headless pipelines and batch generation."),
        bullet_item("<b>Python API</b>  —  Importable module for custom applications, bots, and agent loops."),
    ])

    story.append(Spacer(1, 3*mm))

    # ── 3. TECHNICAL ARCHITECTURE ────────────────────────────────────────────
    story += section("Technical Architecture", [
        Paragraph(
            "SnapVid is built with <b>zero cloud runtime dependencies</b> using only "
            "Python, Pillow, NumPy, and bundled FFmpeg:", body),
    ])

    arch_data = [
        [Paragraph("<b>Layer</b>", table_head),
         Paragraph("<b>Technology</b>", table_head),
         Paragraph("<b>Capability</b>", table_head)],
        [Paragraph("Scene Planner Agent", table_cell),
         Paragraph("Qwen3-4B · GenieX NPU (w4a16)", table_cell),
         Paragraph("JSON scene script + self-healing repair loop (3 retries)", table_cell)],
        [Paragraph("Quality Critic Agent", table_cell),
         Paragraph("Second LLM pass · same model", table_cell),
         Paragraph("Autonomous narration & pacing review", table_cell)],
        [Paragraph("Frame Renderer", table_cell),
         Paragraph("Pillow + NumPy · 1280×720 @ 30 FPS", table_cell),
         Paragraph("10 templates: title, bullets, bar chart, counter, kinetic, code, split, quote, icon list, lower-third", table_cell)],
        [Paragraph("Scene Transitions", table_cell),
         Paragraph("Pure-Python compositor", table_cell),
         Paragraph("Fade, slide, zoom-in, cross-dissolve between scenes", table_cell)],
        [Paragraph("TTS Engine", table_cell),
         Paragraph("Kokoro 82M → Edge TTS → SAPI", table_cell),
         Paragraph("Auto-select offline neural voice; word-level caption sync", table_cell)],
        [Paragraph("Video Mux", table_cell),
         Paragraph("FFmpeg (imageio-ffmpeg bundled)", table_cell),
         Paragraph("H.264 / AAC MP4 — no system ffmpeg install required", table_cell)],
        [Paragraph("Real-time Events", table_cell),
         Paragraph("Server-Sent Events (SSE)", table_cell),
         Paragraph("Live token, validation, render & TTS progress streamed to UI", table_cell)],
        [Paragraph("Test Suite", table_cell),
         Paragraph("pytest · 74 tests", table_cell),
         Paragraph("Schema, LLM, renderer, TTS, server, transitions, history, NPU", table_cell)],
    ]
    arch_table = Table(arch_data,
        colWidths=[42*mm, 50*mm, None],
        repeatRows=1)
    arch_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE_900),
        ("BACKGROUND",    (0,1), (-1,1),  colors.HexColor("#0F172A")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0F1829"), colors.HexColor("#111827")]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#1E293B")),
        ("LINEBELOW",     (0,0), (-1,0),  1.2, VIOLET),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 3*mm))

    # ── 4. NPU BENCHMARKS ────────────────────────────────────────────────────
    story += section("Snapdragon NPU Performance Benchmarks", [
        Paragraph(
            "Verified on <b>Snapdragon X Elite CRD (Hexagon NPU)</b> via Qualcomm AI Hub "
            "cloud profiling with GenieX w4a16 quantization:", body),
    ])

    bench_data = [
        [Paragraph("<b>Component</b>", table_head),
         Paragraph("<b>Hardware</b>", table_head),
         Paragraph("<b>Latency</b>", table_head),
         Paragraph("<b>Throughput</b>", table_head)],
        [Paragraph("Qwen3-4B Scene Planner", table_cell),
         Paragraph("Hexagon NPU (GenieX w4a16)", table_cell),
         Paragraph("~2.1 s / script", table_cell),
         Paragraph("~22.4 tok/s", ParagraphStyle("Green", parent=styles["Normal"],
             fontSize=8.5, leading=12, textColor=GREEN, fontName="Helvetica-Bold"))],
        [Paragraph("Kokoro TTS (per scene)", table_cell),
         Paragraph("CPU ARM64", table_cell),
         Paragraph("~1.8 s / scene", table_cell),
         Paragraph("Real-time ×1.4", table_cell)],
        [Paragraph("Pillow Frame Renderer", table_cell),
         Paragraph("CPU ARM64", table_cell),
         Paragraph("~0.6 s / scene", table_cell),
         Paragraph("30 FPS native", table_cell)],
        [Paragraph("Full Pipeline (60 s video)", table_cell),
         Paragraph("Snapdragon X Elite", table_cell),
         Paragraph("~30 s total", table_cell),
         Paragraph("2× Real-Time", ParagraphStyle("Green2", parent=styles["Normal"],
             fontSize=8.5, leading=12, textColor=AMBER, fontName="Helvetica-Bold"))],
    ]
    bench_table = Table(bench_data,
        colWidths=[50*mm, 52*mm, 32*mm, None],
        repeatRows=1)
    bench_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE_900),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0F1829"), colors.HexColor("#111827")]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#1E293B")),
        ("LINEBELOW",     (0,0), (-1,0),  1.2, CYAN_LIGHT),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ]))
    story.append(bench_table)
    story.append(Spacer(1, 3*mm))

    # ── 5. KEY DIFFERENTIATORS ───────────────────────────────────────────────
    story += section("Key Differentiators vs. Existing Solutions", [])

    diff_data = [
        [Paragraph("<b>Feature</b>", table_head),
         Paragraph("<b>SnapVid</b>", table_head),
         Paragraph("<b>HeyGen / Synthesia</b>", table_head),
         Paragraph("<b>Manim / Remotion</b>", table_head)],
        [Paragraph("Runs offline", table_cell),
         Paragraph("✅ Yes — full NPU", table_cell),
         Paragraph("❌ Cloud required", table_cell),
         Paragraph("⚠️ Partial", table_cell)],
        [Paragraph("Cost", table_cell),
         Paragraph("Free · MIT Open Source", table_cell),
         Paragraph("$24–$119/month", table_cell),
         Paragraph("Free but expert setup", table_cell)],
        [Paragraph("Privacy", table_cell),
         Paragraph("✅ Data never leaves device", table_cell),
         Paragraph("❌ Uploads your content", table_cell),
         Paragraph("✅ Local", table_cell)],
        [Paragraph("Setup time", table_cell),
         Paragraph("pip install + 1 command", table_cell),
         Paragraph("Account + subscription", table_cell),
         Paragraph("Hours (LaTeX/Node deps)", table_cell)],
        [Paragraph("Video in 60 s", table_cell),
         Paragraph("✅ ~30 s on Snapdragon", table_cell),
         Paragraph("⚠️ Minutes (cloud queue)", table_cell),
         Paragraph("❌ Hours (render compile)", table_cell)],
        [Paragraph("Snapdragon NPU", table_cell),
         Paragraph("✅ Hexagon NPU via GenieX", table_cell),
         Paragraph("❌ No", table_cell),
         Paragraph("❌ No", table_cell)],
    ]
    diff_table = Table(diff_data,
        colWidths=[42*mm, 44*mm, 45*mm, None],
        repeatRows=1)
    diff_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE_900),
        ("BACKGROUND",    (0,1), (-1,1),  colors.HexColor("#0B1625")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0B1625"), colors.HexColor("#0F1829")]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#1E293B")),
        ("LINEBELOW",     (0,0), (-1,0),  1.2, GREEN),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ]))
    story.append(diff_table)
    story.append(Spacer(1, 3*mm))

    # ── 6. USE CASES & TARGET USERS ─────────────────────────────────────────
    story += section("Target Users & Use Cases", [
        bullet_item("<b>School & Coaching Institute Teachers</b>  —  Generate curriculum explainer videos for offline classrooms."),
        bullet_item("<b>YouTube Educators</b>  —  Rapid STEM and tutorial video drafts without a studio."),
        bullet_item("<b>Corporate L&D Teams</b>  —  Internal training modules with zero data exposure."),
        bullet_item("<b>Small Business Owners</b>  —  Product explainers in local language, offline, at zero cost."),
        bullet_item("<b>Developers & Data Scientists</b>  —  Automated documentation and concept visualization pipelines."),
    ])
    story.append(Spacer(1, 3*mm))

    # ── 7. TECHNOLOGY STACK ──────────────────────────────────────────────────
    story += section("Technology Stack", [])

    stack_data = [
        [Paragraph("<b>Category</b>", table_head),
         Paragraph("<b>Technology</b>", table_head)],
        [Paragraph("Language / Runtime", table_cell),
         Paragraph("Python 3.11+", table_cell)],
        [Paragraph("LLM Inference (NPU)", table_cell),
         Paragraph("Qualcomm GenieX · Hexagon NPU · w4a16 quantization · Qwen3-4B-Instruct", table_cell)],
        [Paragraph("LLM Inference (CPU/Cloud)", table_cell),
         Paragraph("Ollama · llama.cpp · OpenAI · Groq · NVIDIA NIM · Google Gemini", table_cell)],
        [Paragraph("Frame Rendering", table_cell),
         Paragraph("Pillow ≥10.0 · NumPy ≥1.26 · Custom easing engine", table_cell)],
        [Paragraph("Video Encoding", table_cell),
         Paragraph("FFmpeg (bundled via imageio-ffmpeg) · H.264 + AAC · MP4", table_cell)],
        [Paragraph("Text-to-Speech", table_cell),
         Paragraph("Kokoro 82M (neural, offline) · Edge TTS · Windows SAPI", table_cell)],
        [Paragraph("Schema Validation", table_cell),
         Paragraph("Pydantic v2 · JSON repair loop (3 retries)", table_cell)],
        [Paragraph("Web Server / API", table_cell),
         Paragraph("FastAPI · SSE streaming · CORS · REST endpoints", table_cell)],
        [Paragraph("Frontend", table_cell),
         Paragraph("Vanilla HTML5 / CSS3 / JS · Aurora UI · Plus Jakarta Sans · JetBrains Mono", table_cell)],
        [Paragraph("Testing", table_cell),
         Paragraph("pytest · 74 tests · 100% passing", table_cell)],
        [Paragraph("License", table_cell),
         Paragraph("MIT Open Source", table_cell)],
    ]
    stack_table = Table(stack_data,
        colWidths=[48*mm, None],
        repeatRows=1)
    stack_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE_900),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0F1829"), colors.HexColor("#111827")]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#1E293B")),
        ("LINEBELOW",     (0,0), (-1,0),  1.2, FUCHSIA),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ]))
    story.append(stack_table)
    story.append(Spacer(1, 3*mm))

    # ── 8. INNOVATION SUMMARY ────────────────────────────────────────────────
    story += section("Innovation Highlights", [
        bullet_item("<b>Self-Healing Agentic Pipeline</b>  —  Invalid JSON from the LLM triggers an automatic repair prompt loop (up to 3 retries) before failing."),
        bullet_item("<b>Two-Agent Architecture</b>  —  Scene Planner agent + independent Quality Critic agent reviewing pacing, clarity, and narration."),
        bullet_item("<b>Audio-First Rendering</b>  —  Narration is synthesised first, scene durations are reconciled to audio, then frames are rendered — guaranteeing perfect A/V sync."),
        bullet_item("<b>Word-Level Caption Overlay</b>  —  On-screen captions are timed to individual word offsets within each audio chunk, providing karaoke-style display."),
        bullet_item("<b>Animated Scene Transitions</b>  —  Smooth fade, slide, zoom-in, and cross-dissolve transitions composited in pure Python between scenes."),
        bullet_item("<b>Configurable at Runtime</b>  —  LLM provider, model, API key, voice engine, and video format all switchable live from the web UI — no code changes required."),
    ])
    story.append(Spacer(1, 3*mm))

    # ── 9. ROADMAP ────────────────────────────────────────────────────────────
    story += section("Roadmap", [
        bullet_item("<b>Multilingual TTS</b>  —  Hindi & regional language voice via Meta MMS-TTS."),
        bullet_item("<b>On-Device Captions via Whisper NPU</b>  —  Animated karaoke subtitles transcribed locally on Snapdragon NPU."),
        bullet_item("<b>GIF / WebM / Vertical 9:16 Export</b>  —  Mobile-first shorts and social media clips."),
        bullet_item("<b>Slide Import</b>  —  PPTX → video pipeline using existing template system."),
    ])

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=VIOLET,
                            spaceAfter=4, spaceBefore=0))
    story.append(Paragraph(
        "SnapVid  ·  github.com/GoDxVictoryRR/snapvid  ·  MIT License  ·  "
        f"Generated {datetime.date.today().strftime('%d %B %Y')}",
        footer_style
    ))

    # ── Page background drawing ──────────────────────────────────────────────
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(OBSIDIAN)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"[OK] Brief saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    build_brief()
