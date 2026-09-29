"""SnapReel CLI entry point.

Usage:
    python run.py "Explain photosynthesis in 60 seconds"
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import sys
import time

import dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
dotenv.load_dotenv()

from snapreel.planner import generate
from snapreel.renderer import render_video
from snapreel.tts import narrate


def main(topic: str) -> str:
    """Plan, narrate, and render an explainer video for a given topic.

    Args:
        topic: Subject matter to explain.

    Returns:
        Path to the rendered MP4 video.
    """
    logging.info("Planning video for topic: %s", topic)
    script = generate(topic)
    logging.info("Generated script '%s' with %d scenes (total %.1fs)", script.title, len(script.scenes), script.total_duration)

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", topic[:30].strip().lower()).strip("_") or "video"
    ts = int(time.time())
    out_path = str(out_dir / f"{slug}_{ts}.mp4")

    # Attempt TTS narration if supported on this platform
    audio_path = None
    try:
        full_narration = " ... ".join(s.narration for s in script.scenes if s.narration)
        if full_narration:
            wav_path = str(out_dir / f"{slug}_{ts}_narration.wav")
            logging.info("Synthesizing narration audio...")
            narrate(full_narration, wav_path)
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                audio_path = wav_path
                logging.info("Narration audio generated: %s", audio_path)
    except Exception as exc:
        logging.warning("TTS audio generation skipped: %s", exc)

    def progress(i: int, total: int):
        logging.info("Rendering scene %d/%d...", i + 1, total)

    render_video(script, out_path, audio_path=audio_path, on_progress=progress)
    logging.info("Video rendering complete: %s", out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python run.py "your topic"')
        sys.exit(1)
    main(" ".join(sys.argv[1:]))
