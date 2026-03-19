"""Mistral AI service: audio transcription (Voxtral)."""

import logging

from mistralai import Mistral

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_client() -> Mistral:
    """Instantiate a Mistral client with the configured API key."""
    return Mistral(api_key=get_settings().mistral_api_key)


# ---------------------------------------------------------------------------
# 1. Audio transcription via Voxtral
# ---------------------------------------------------------------------------
async def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """Transcribe audio bytes using Voxtral and return the text transcript.

    Uses the dedicated audio.transcriptions endpoint from the Mistral SDK.
    """
    client = _get_client()

    # Determine MIME type from extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    mime_map = {
        "webm": "audio/webm",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "m4a": "audio/mp4",
    }
    content_type = mime_map.get(ext, "audio/webm")

    logger.info("Transcribing %s (%s, %d bytes)…", filename, content_type, len(file_bytes))

    response = await client.audio.transcriptions.complete_async(
        model=get_settings().voice_model,
        file={
            "file_name": filename,
            "content": file_bytes,
            "content_type": content_type,
        },
        language="fr",
    )

    transcript = response.text.strip()
    logger.info("Transcription OK (%d chars)", len(transcript))
    return transcript