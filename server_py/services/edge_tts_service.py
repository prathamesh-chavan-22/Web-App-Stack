import logging
import os

import edge_tts

logger = logging.getLogger(__name__)

VOICE = "en-US-AriaNeural"
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "audio")


async def generate_audio(text: str, filename: str) -> str:
    """Generate MP3 audio from text using Edge TTS. Returns URL path."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    filepath = os.path.join(AUDIO_DIR, filename)

    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(filepath)
        return f"/static/audio/{filename}"
    except Exception as e:
        logger.error(f"Edge TTS generation failed for {filename}: {e}")
        raise
