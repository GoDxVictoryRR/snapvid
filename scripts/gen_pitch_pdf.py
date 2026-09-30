"""
SnapVid — Short Pitch Presentation PDF Generator
Creates a polished multi-slide PDF pitch deck.
"""

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import HorizontalBarChart
import datetime

OUTPUT_PATH = "SnapVid_Pitch_Presentation.pdf"

PAGE_W, PAGE_H = landscape(A4)   # 297 × 210 mm
L_MARGIN = R_MARGIN = 18 * mm
T_MARGIN = B_MARGIN = 14 * mm
USABLE_W = PAGE_W - L_MARGIN - R_MARGIN  # ~261 mm

# Palette
OBSIDIAN   = colors.HexColor("#080B13")
SLATE_900  = colors.HexColor("#0F172A")
SLATE_800  = colors.HexColor("#1E293B")
SLATE_600  = colors.HexColor("#475569")
SLATE_300  = colors.HexColor("#CBD5E1")
SLATE_200  = colors.HexColor("#E2E8F0")
WHITE      = colors.white
FUCHSIA    = colors.HexColor("#EC4899")
VIOLET     = colors.HexColor("#8B5CF6")
CYAN       = colors.HexColor("#06B6D4")
CYAN_LIGHT = colors.HexColor("#38BDF8")
GREEN      = colors.HexColor("#10B981")
AMBER      = colors.HexColor("#F59E0B")
ROSE       = colors.HexColor("#F43F5E")

styles = getSampleStyleSheet()

def style(name, **kw):
    return ParagraphStyle(name, parent=styles["Normal"], **kw)

# Shared styles
TITLE_BIG  = style("TBig", fontSize=38, leading=44, fontName="Helvetica-Bold",
                   textColor=WHITE, alignment=TA_CENTER)
TITLE_SUB  = style("TSub", fontSize=14, leading=20, fontName="Helvetica",
                   textColor=CYAN_LIGHT, alignment=TA_CENTER, spaceAfter=6)
SLIDE_HEAD = style("SH",   fontSize=26, leading=32, fontName="Helvetica-Bold",
                   textColor=WHITE, spaceAfter=4)
SLIDE_SUB  = style("SS",   fontSize=12, leading=16, fontName="Helvetica",
                   textColor=CYAN_LIGHT, spaceAfter=8)
BODY       = style("Bod",  fontSize=11, leading=16, fontName="Helvetica",
                   textColor=SLATE_200, alignment=TA_JUSTIFY)
BULLET     = style("Bul",  fontSize=11, leading=17, fontName="Helvetica",
                   textColor=SLATE_200, leftIndent=14, spaceAfter=4)
BIG_STAT   = style("BS",   fontSize=46, leading=52, fontName="Helvetica-Bold",
                   textColor=FUCHSIA, alignment=TA_CENTER)
BIG_LABEL  = style("BL",   fontSize=11, leading=14, fontName="Helvetica",
                   textColor=SLATE_300, alignment=TA_CENTER)
TABLE_H    = style("TH",   fontSize=9.5, leading=13, fontName="Helvetica-Bold",
                   textColor=WHITE)
TABLE_C    = style("TC",   fontSize=9,   leading=13, fontName="Helvetica",
                   textColor=SLATE_200)
FOOTER     = style("Ft",   fontSize=7.5, leading=11, fontName="Helvetica",
                   textColor=SLATE_600, alignment=TA_CENTER)
SLIDE_NUM  = style("SN",   fontSize=8,   fontName="Helvetica",
                   textColor=SLATE_600, alignment=TA_RIGHT)

TICK_GREEN = style("TG", fontSize=11, fontName="Helvetica-Bold", textColor=GREEN)
CROSS_RED  = style("CR", fontSize=11, fontName="Helvetica-Bold", textColor=ROSE)

def p(text, s=BODY): return Paragraph(text, s)
def sp(h=4): return Spacer(1, h*mm)
def hr(color=VIOLET): return HRFlowable(width="100%", thickness=1.0,
                                         color=color, spaceAfter=5, spaceBefore=0)
def pb(): return PageBreak()

def bullet_item(text, icon="►"):
    return p(f"{icon} {text}", BULLET)

# ─── page background callback ────────────────────────────────────────────────
SLIDE_NUM_COUNTER = [0]

def on_page(canvas, doc):
    SLIDE_NUM_COUNTER[0] += 1
    n = SLIDE_NUM_COUNTER[0]
    total = 10  # total slides

    canvas.saveState()
    # Background
    canvas.setFillColor(OBSIDIAN)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Top accent bar
    canvas.setFillColor(SLATE_900)
    canvas.rect(0, PAGE_H - 12*mm, PAGE_W, 12*mm, fill=1, stroke=0)

    # Bottom accent bar
    canvas.setFillColor(SLATE_900)
    canvas.rect(0, 0, PAGE_W, 10*mm, fill=1, stroke=0)

    # Gradient-ish accent line under top bar
    for i, clr in enumerate([FUCHSIA, VIOLET, CYAN]):
        canvas.setFillColor(clr)
        canvas.rect(i*(PAGE_W/3), PAGE_H - 12*mm, PAGE_W/3, 2.5, fill=1, stroke=0)

    # Slide number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE_600)
    canvas.drawRightString(PAGE_W - L_MARGIN, 3*mm, f"{n} / {total}")

    # Brand in top-left
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(FUCHSIA)
    canvas.drawString(L_MARGIN, PAGE_H - 8.5*mm, "Snap")
    canvas.setFillColor(WHITE)
    canvas.drawString(L_MARGIN + 26, PAGE_H - 8.5*mm, "Vid")

    # Tagline in top-right
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE_600)
    canvas.drawRightString(PAGE_W - R_MARGIN, PAGE_H - 8.5*mm, "Snapdragon AI Lab Challenge 2026")

    canvas.restoreState()


def accent_box(story, title, sub, body_flowables):
    """Styled content block with fuchsia accent left border."""
    content = Table(
        [[Table([[p(title, SLIDE_HEAD)],
                 [p(sub, SLIDE_SUB)]], colWidths=[USABLE_W - 6*mm])
         ]] +
        [[f] for f in body_flowables],
        colWidths=[USABLE_W]
    )
    content.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(content)


# ─── BUILD SLIDES ────────────────────────────────────────────────────────────
def build_pitch():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=landscape(A4),
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN + 8*mm, bottomMargin=B_MARGIN + 8*mm,
        title="SnapVid — Short Pitch Presentation",
        author="GoDxVictoryRR / SnapVid",
    )
    story = []

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 1 — TITLE
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        sp(22),
        p('<font color="#EC4899"><b>Snap</b></font>'
          '<font color="#FFFFFF"><b>Vid</b></font>', TITLE_BIG),
        sp(3),
        p("Offline Agentic AI Video Maker · On-Device Snapdragon NPU", TITLE_SUB),
        sp(5),
        p("Turning a plain-text prompt into a polished, narrated, animated video "
          "— <b>in under 60 seconds</b> — with <b>zero cloud, zero subscription, "
          "zero internet.</b>",
          style("TS", fontSize=14, leading=20, fontName="Helvetica",
                textColor=SLATE_300, alignment=TA_CENTER)),
        sp(8),
        Table([
            [p("github.com/GoDxVictoryRR/snapvid",
               style("GH", fontSize=10, textColor=CYAN_LIGHT,
                     fontName="Helvetica-Bold", alignment=TA_CENTER)),
             p("MIT Open Source",
               style("MIT", fontSize=10, textColor=GREEN,
                     fontName="Helvetica-Bold", alignment=TA_CENTER)),
             p("74/74 Tests Passing",
               style("T74", fontSize=10, textColor=AMBER,
                     fontName="Helvetica-Bold", alignment=TA_CENTER))
            ]
        ], colWidths=[USABLE_W/3]*3),
        pb()
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 2 — THE PROBLEM
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("The Problem", SLIDE_HEAD),
        hr(ROSE),
        p("Professional explainer videos are expensive, cloud-locked, and privacy-invasive.", SLIDE_SUB),
        sp(4),
        Table([
            [
                Table([
                    [p("₹5,000", style("BigStat2", fontSize=40, leading=48,
                                       fontName="Helvetica-Bold", textColor=ROSE,
                                       alignment=TA_CENTER))],
                    [p("Minimum cost per HeyGen / Synthesia video", BIG_LABEL)],
                ], colWidths=[80*mm]),
                Table([
                    [p("0 Mbps", style("BigStat3", fontSize=40, leading=48,
                                       fontName="Helvetica-Bold", textColor=AMBER,
                                       alignment=TA_CENTER))],
                    [p("Internet available in rural Indian classrooms", BIG_LABEL)],
                ], colWidths=[80*mm]),
                Table([
                    [p("100%", style("BigStat4", fontSize=40, leading=48,
                                     fontName="Helvetica-Bold", textColor=ROSE,
                                     alignment=TA_CENTER))],
                    [p("Of these tools upload your private content to the cloud", BIG_LABEL)],
                ], colWidths=[USABLE_W - 160*mm]),
            ]
        ], colWidths=[80*mm, 80*mm, None]),
        sp(6),
        Table([
            [bullet_item("<b>Educators, coaches, and small businesses</b> need video content but cannot afford cloud video tools."),
             bullet_item("<b>Snapdragon X Elite laptops</b> have the NPU horsepower — but no tool uses it for video creation.")],
            [bullet_item("<b>Privacy matters</b> — lecture notes, trade secrets, and student data should <b>never</b> leave the device."),
             bullet_item("<b>Bandwidth is scarce</b> — offline-first tools are essential for Tier-2/3 cities and remote areas.")]
        ], colWidths=[USABLE_W/2, USABLE_W/2]),
        pb()
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 3 — THE SOLUTION
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("The Solution", SLIDE_HEAD),
        hr(GREEN),
        p("SnapVid — One prompt. 60 seconds. One polished video. No cloud.", SLIDE_SUB),
        sp(4),
        Table([
            [
                Table([
                    [p("🖥️  Browser UI", style("Mode1", fontSize=13, fontName="Helvetica-Bold",
                                                textColor=FUCHSIA))],
                    [p("Dark-mode studio with live agent activity log, settings panel, history, and built-in video player.", BODY)],
                    [sp(2)],
                    [p("⌨️  CLI", style("Mode2", fontSize=13, fontName="Helvetica-Bold",
                                         textColor=VIOLET))],
                    [p("python run.py \"topic\" — headless, scriptable, batch-ready.", BODY)],
                    [sp(2)],
                    [p("🐍  Python API", style("Mode3", fontSize=13, fontName="Helvetica-Bold",
                                               textColor=CYAN_LIGHT))],
                    [p("from snapreel.planner import generate — importable into any application.", BODY)],
                ], colWidths=[115*mm]),
                Table([
                    [p("How it works:", style("HW", fontSize=12, fontName="Helvetica-Bold",
                                              textColor=WHITE))],
                    [sp(2)],
                    [bullet_item("User types a topic in plain English")],
                    [bullet_item("Scene Planner Agent generates structured JSON scene script via NPU")],
                    [bullet_item("Self-healing validator checks and repairs the JSON (3 retries)")],
                    [bullet_item("Quality Critic Agent reviews pacing and narration")],
                    [bullet_item("Kokoro TTS synthesises audio offline — word-level caption sync")],
                    [bullet_item("Pure-Python renderer draws animated frames at 30 FPS")],
                    [bullet_item("FFmpeg muxes video + audio → polished MP4 in ~30 seconds")],
                ], colWidths=[USABLE_W - 115*mm]),
            ]
        ], colWidths=[115*mm, None]),
        pb()
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 4 — TECHNICAL ARCHITECTURE
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("Technical Architecture", SLIDE_HEAD),
        hr(VIOLET),
        p("Two-agent pipeline · Pure Python · Zero Node.js · Zero cloud runtime dependencies", SLIDE_SUB),
        sp(3),
        Table([
            [p("<b>Component</b>", TABLE_H),
             p("<b>Technology</b>", TABLE_H),
             p("<b>Detail</b>", TABLE_H)],
            [p("LLM Inference (NPU)", TABLE_C),
             p("Qualcomm GenieX · Hexagon NPU · w4a16", TABLE_C),
             p("OpenAI-compatible endpoint · auto-selected by provider setting", TABLE_C)],
            [p("Agent Loop", TABLE_C),
             p("Scene Planner + Quality Critic · Pydantic v2", TABLE_C),
             p("JSON validation · self-healing repair prompt · SSE event stream", TABLE_C)],
            [p("Frame Renderer", TABLE_C),
             p("Pillow ≥10 · NumPy ≥1.26 · 1280×720 @ 30 FPS", TABLE_C),
             p("10 animated templates · easing curves · grain overlay", TABLE_C)],
            [p("Transitions", TABLE_C),
             p("Pure-Python compositor", TABLE_C),
             p("Fade · slide · zoom-in · cross-dissolve between scenes", TABLE_C)],
            [p("TTS Engine", TABLE_C),
             p("Kokoro 82M → Edge TTS → SAPI", TABLE_C),
             p("Auto-selected · word-level caption timing · fully offline", TABLE_C)],
            [p("Video Mux", TABLE_C),
             p("imageio-ffmpeg (bundled)", TABLE_C),
             p("No system ffmpeg install · H.264 + AAC MP4 container", TABLE_C)],
            [p("Web UI", TABLE_C),
             p("FastAPI · SSE · HTML/CSS/JS", TABLE_C),
             p("Real-time agent log · settings modal · history · video player", TABLE_C)],
            [p("Tests", TABLE_C),
             p("pytest · 74 tests · 100% passing", TABLE_C),
             p("Schema · LLM · renderer · TTS · server · transitions · NPU · history", TABLE_C)],
        ], colWidths=[48*mm, 68*mm, None], repeatRows=1),
        pb()
    ]
    story[-2].setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE_900),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0F1829"), SLATE_900]),
        ("GRID",          (0,0), (-1,-1), 0.4, SLATE_800),
        ("LINEBELOW",     (0,0), (-1,0),  1.2, VIOLET),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ]))

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 5 — NPU BENCHMARKS
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("Snapdragon NPU Performance", SLIDE_HEAD),
        hr(CYAN),
        p("Verified on Snapdragon X Elite CRD via Qualcomm AI Hub · GenieX w4a16 quantization", SLIDE_SUB),
        sp(5),
        Table([
            [
                Table([
                    [p("~22.4", BIG_STAT)],
                    [p("Tokens / Second on Hexagon NPU", BIG_LABEL)],
                ], colWidths=[60*mm]),
                Table([
                    [p("~30s", style("BS2", fontSize=46, leading=52, fontName="Helvetica-Bold",
                                     textColor=GREEN, alignment=TA_CENTER))],
                    [p("Full 60-second video, end-to-end", BIG_LABEL)],
                ], colWidths=[60*mm]),
                Table([
                    [p("2×", style("BS3", fontSize=46, leading=52, fontName="Helvetica-Bold",
                                   textColor=AMBER, alignment=TA_CENTER))],
                    [p("Faster than Real-Time on Snapdragon X Elite", BIG_LABEL)],
                ], colWidths=[USABLE_W - 120*mm]),
            ]
        ], colWidths=[60*mm, 60*mm, None]),
        sp(5),
        Table([
            [p("<b>Pipeline Stage</b>", TABLE_H),
             p("<b>Hardware</b>", TABLE_H),
             p("<b>Latency</b>", TABLE_H),
             p("<b>Throughput</b>", TABLE_H)],
            [p("Qwen3-4B Scene Planner", TABLE_C),
             p("Hexagon NPU (GenieX w4a16)", TABLE_C),
             p("~2.1 s / script", TABLE_C),
             p('<font color="#10B981"><b>~22.4 tok/s</b></font>', TABLE_C)],
            [p("Kokoro TTS", TABLE_C),
             p("CPU ARM64", TABLE_C),
             p("~1.8 s / scene", TABLE_C),
             p("Real-time ×1.4", TABLE_C)],
            [p("Pillow Renderer", TABLE_C),
             p("CPU ARM64", TABLE_C),
             p("~0.6 s / scene", TABLE_C),
             p("30 FPS native", TABLE_C)],
            [p("Full Pipeline", TABLE_C),
             p('<b><font color="#F59E0B">Snapdragon X Elite</font></b>', TABLE_C),
             p('<b><font color="#F59E0B">~30 s total</font></b>', TABLE_C),
             p('<b><font color="#F59E0B">60 s video</font></b>', TABLE_C)],
        ], colWidths=[62*mm, 65*mm, 45*mm, None], repeatRows=1),
        pb()
    ]
    story[-2].setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE_900),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0F1829"), SLATE_900]),
        ("GRID",          (0,0), (-1,-1), 0.4, SLATE_800),
        ("LINEBELOW",     (0,0), (-1,0),  1.2, CYAN),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ]))

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 6 — COMPETITIVE LANDSCAPE
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("Competitive Landscape", SLIDE_HEAD),
        hr(GREEN),
        p("SnapVid wins on every axis that matters for offline, privacy-first video creation.", SLIDE_SUB),
        sp(3),
        Table([
            [p("<b>Feature</b>", TABLE_H),
             p('<font color="#EC4899"><b>SnapVid</b></font>', TABLE_H),
             p("<b>HeyGen / Synthesia</b>", TABLE_H),
             p("<b>Manim / Remotion</b>", TABLE_H)],
            [p("Offline / No internet", TABLE_C),
             p('<font color="#10B981"><b>✅ Full NPU pipeline</b></font>', TABLE_C),
             p('<font color="#F43F5E">❌ Cloud required</font>', TABLE_C),
             p('<font color="#F59E0B">⚠️ Partial</font>', TABLE_C)],
            [p("Cost", TABLE_C),
             p('<font color="#10B981"><b>Free · MIT Open Source</b></font>', TABLE_C),
             p("$24–$119 / month", TABLE_C),
             p("Free (expert setup)", TABLE_C)],
            [p("Privacy (data stays on device)", TABLE_C),
             p('<font color="#10B981"><b>✅ Never leaves device</b></font>', TABLE_C),
             p('<font color="#F43F5E">❌ Uploads content</font>', TABLE_C),
             p('<font color="#10B981">✅ Local</font>', TABLE_C)],
            [p("Setup time", TABLE_C),
             p('<font color="#10B981"><b>pip install + 1 command</b></font>', TABLE_C),
             p("Account + subscription + onboard", TABLE_C),
             p("Hours (LaTeX / Node deps)", TABLE_C)],
            [p("60 s video speed", TABLE_C),
             p('<font color="#10B981"><b>~30 s on Snapdragon</b></font>', TABLE_C),
             p("Minutes (cloud queue)", TABLE_C),
             p('<font color="#F43F5E">❌ Render compile hours</font>', TABLE_C)],
            [p("Snapdragon NPU acceleration", TABLE_C),
             p('<font color="#10B981"><b>✅ Hexagon NPU via GenieX</b></font>', TABLE_C),
             p('<font color="#F43F5E">❌ None</font>', TABLE_C),
             p('<font color="#F43F5E">❌ None</font>', TABLE_C)],
            [p("API / CLI access", TABLE_C),
             p('<font color="#10B981"><b>✅ Browser + CLI + Python API</b></font>', TABLE_C),
             p("Web only", TABLE_C),
             p("Script only", TABLE_C)],
        ], colWidths=[52*mm, 60*mm, 60*mm, None], repeatRows=1),
        pb()
    ]
    story[-2].setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  SLATE_900),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0B1625"), SLATE_900]),
        ("GRID",          (0,0), (-1,-1), 0.4, SLATE_800),
        ("LINEBELOW",     (0,0), (-1,0),  1.5, GREEN),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 7 — KEY INNOVATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("Key Innovations", SLIDE_HEAD),
        hr(FUCHSIA),
        p("Six technical breakthroughs that make SnapVid uniquely powerful.", SLIDE_SUB),
        sp(4),
        Table([
            [
                Table([
                    [p("🔁  Self-Healing JSON Agent", style("I1", fontSize=12, fontName="Helvetica-Bold", textColor=FUCHSIA))],
                    [p("Invalid LLM output triggers automatic repair prompt loop — up to 3 retries — before failing gracefully.", BODY)],
                    [sp(3)],
                    [p("🎙️  Audio-First Rendering", style("I2", fontSize=12, fontName="Helvetica-Bold", textColor=VIOLET))],
                    [p("Narration synthesised first; scene durations reconciled to audio length — guaranteeing perfect A/V sync.", BODY)],
                    [sp(3)],
                    [p("📝  Word-Level Caption Sync", style("I3", fontSize=12, fontName="Helvetica-Bold", textColor=CYAN_LIGHT))],
                    [p("On-screen captions timed to individual word offsets within each audio chunk — karaoke-style display.", BODY)],
                ], colWidths=[125*mm]),
                Table([
                    [p("🤖  Two-Agent Architecture", style("I4", fontSize=12, fontName="Helvetica-Bold", textColor=GREEN))],
                    [p("Scene Planner agent generates content; Quality Critic agent independently reviews pacing, clarity and narration before render.", BODY)],
                    [sp(3)],
                    [p("🎞️  Animated Transitions", style("I5", fontSize=12, fontName="Helvetica-Bold", textColor=AMBER))],
                    [p("Smooth fade, slide, zoom-in, and cross-dissolve transitions composited in pure Python — no external video library.", BODY)],
                    [sp(3)],
                    [p("⚡  Live-Config from UI", style("I6", fontSize=12, fontName="Helvetica-Bold", textColor=FUCHSIA))],
                    [p("LLM provider, model, API key, voice, and format all switchable live from the settings drawer — no code changes.", BODY)],
                ], colWidths=[USABLE_W - 125*mm]),
            ]
        ], colWidths=[125*mm, None]),
        pb()
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 8 — TARGET USERS & IMPACT
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("Target Users & Real-World Impact", SLIDE_HEAD),
        hr(AMBER),
        p("SnapVid democratises professional video creation for the next billion users.", SLIDE_SUB),
        sp(4),
        Table([
            [p("🎓  School & Coaching Teachers",
               style("U1", fontSize=12, fontName="Helvetica-Bold", textColor=CYAN_LIGHT)),
             p("📺  YouTube Educators",
               style("U2", fontSize=12, fontName="Helvetica-Bold", textColor=VIOLET)),
             p("🏢  Corporate L&D Teams",
               style("U3", fontSize=12, fontName="Helvetica-Bold", textColor=FUCHSIA))],
            [p("Generate curriculum explainer videos for offline classrooms. Zero cost. Zero internet.", BODY),
             p("Rapid STEM tutorial video drafts without a recording studio or video editor subscription.", BODY),
             p("Internal training modules with zero data-exposure risk — content stays on-device.", BODY)],
            [sp(3), sp(3), sp(3)],
            [p("🛍️  Small Business Owners",
               style("U4", fontSize=12, fontName="Helvetica-Bold", textColor=GREEN)),
             p("👨‍💻  Developers & Data Scientists",
               style("U5", fontSize=12, fontName="Helvetica-Bold", textColor=AMBER)),
             p("🌐  NGOs & Rural Education",
               style("U6", fontSize=12, fontName="Helvetica-Bold", textColor=ROSE))],
            [p("Product explainers in local language, offline, at zero cost — built in under 60 seconds.", BODY),
             p("Automated documentation, concept visualization pipelines, and API-first video generation.", BODY),
             p("Offline video content creation for areas with no reliable internet — runs on battery power.", BODY)],
        ], colWidths=[USABLE_W/3, USABLE_W/3, None]),
        pb()
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 9 — DEMO & TECH STACK
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        p("Technology Stack & Demo", SLIDE_HEAD),
        hr(VIOLET),
        p("Fully open source · MIT License · github.com/GoDxVictoryRR/snapvid", SLIDE_SUB),
        sp(3),
        Table([
            [
                Table([
                    [p("Core Stack", style("CS", fontSize=12, fontName="Helvetica-Bold", textColor=FUCHSIA))],
                    [sp(2)],
                    [bullet_item("<b>Python 3.11+</b>  —  Pillow, NumPy, FastAPI, Pydantic v2")],
                    [bullet_item("<b>imageio-ffmpeg</b>  —  Bundled FFmpeg binary")],
                    [bullet_item("<b>Qualcomm GenieX</b>  —  NPU LLM inference")],
                    [bullet_item("<b>Kokoro 82M TTS</b>  —  Offline neural voice")],
                    [bullet_item("<b>Ollama / llama.cpp</b>  —  CPU/GPU fallback")],
                    [bullet_item("<b>OpenAI / Groq / NIM / Gemini</b>  —  Cloud options")],
                    [sp(3)],
                    [p("Supported Providers", style("SP", fontSize=12, fontName="Helvetica-Bold", textColor=CYAN_LIGHT))],
                    [sp(2)],
                    [bullet_item("Qualcomm GenieX (NPU)  · Ollama  · llama.cpp")],
                    [bullet_item("OpenAI  · Groq  · NVIDIA NIM  · Google Gemini")],
                    [bullet_item("Together AI  · Mistral AI  · Any OpenAI-compatible API")],
                ], colWidths=[120*mm]),
                Table([
                    [p("Quick Start", style("QS", fontSize=12, fontName="Helvetica-Bold", textColor=GREEN))],
                    [sp(2)],
                    [p("""<font face="Courier" color="#94A3B8">git clone github.com/GoDxVictoryRR/snapvid
cd snapvid
pip install -r requirements.txt
cp .env.example .env
python -m snapreel.server</font>""",
                       style("Code", fontSize=9, leading=14, fontName="Courier",
                             textColor=SLATE_300,
                             backColor=colors.HexColor("#0A0F1E")))],
                    [sp(3)],
                    [p("Test Suite", style("TS2", fontSize=12, fontName="Helvetica-Bold", textColor=AMBER))],
                    [sp(2)],
                    [p('<font color="#10B981"><b>74 / 74 tests passing</b></font>',
                       style("T74b", fontSize=24, leading=30, fontName="Helvetica-Bold",
                             alignment=TA_CENTER))],
                    [p("Schema · LLM · Renderer · TTS · Server · Transitions · NPU · History",
                       style("T74c", fontSize=9, textColor=SLATE_300, alignment=TA_CENTER))],
                ], colWidths=[USABLE_W - 120*mm]),
            ]
        ], colWidths=[120*mm, None]),
        pb()
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # SLIDE 10 — CLOSING / CTA
    # ═══════════════════════════════════════════════════════════════════════════
    story += [
        sp(14),
        p('<font color="#EC4899"><b>Snap</b></font><font color="#FFFFFF"><b>Vid</b></font>',
          style("CloseLogo", fontSize=44, leading=50, fontName="Helvetica-Bold",
                alignment=TA_CENTER)),
        sp(3),
        p("The only offline, NPU-accelerated, privacy-first AI video maker.",
          style("ClSub", fontSize=16, leading=22, fontName="Helvetica",
                textColor=CYAN_LIGHT, alignment=TA_CENTER)),
        sp(6),
        Table([
            [p("🌟  Free Forever", style("C1", fontSize=13, fontName="Helvetica-Bold",
                                          textColor=FUCHSIA, alignment=TA_CENTER)),
             p("⚡  30 sec / video", style("C2", fontSize=13, fontName="Helvetica-Bold",
                                            textColor=VIOLET, alignment=TA_CENTER)),
             p("🔒  100% On-Device", style("C3", fontSize=13, fontName="Helvetica-Bold",
                                             textColor=GREEN, alignment=TA_CENTER)),
             p("🚀  MIT Open Source", style("C4", fontSize=13, fontName="Helvetica-Bold",
                                              textColor=AMBER, alignment=TA_CENTER))],
        ], colWidths=[USABLE_W/4]*4),
        sp(6),
        p("github.com/GoDxVictoryRR/snapvid",
          style("GHL", fontSize=14, fontName="Helvetica-Bold",
                textColor=CYAN_LIGHT, alignment=TA_CENTER)),
        sp(2),
        p(f"Snapdragon AI Lab Challenge  ·  {datetime.date.today().strftime('%B %Y')}",
          FOOTER),
    ]

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"[OK] Pitch PDF saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pitch()
