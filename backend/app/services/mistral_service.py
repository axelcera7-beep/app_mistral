"""Mistral AI service: audio transcription (Voxtral) and task extraction (Mistral Small)."""

import json
import logging

from mistralai import Mistral

from app.config import get_settings
from app.schemas import TaskItem, TaskListResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model identifiers
# ---------------------------------------------------------------------------
VOXTRAL_MODEL = "voxtral-mini-latest"
TEXT_MODEL = "mistral-small-latest"

# ---------------------------------------------------------------------------
# System prompt for task extraction
# ---------------------------------------------------------------------------
EXTRACT_SYSTEM_PROMPT = """Tu es un assistant expert en productivité.
L'utilisateur t'envoie la transcription brute d'un braindump vocal (un déballage de pensées).

Ton travail :
1. Identifier chaque tâche ou action concrète mentionnée.
2. Pour chaque tâche, fournir :
   - **title** : un titre court et actionnable (commence par un verbe).
   - **description** : une phrase de contexte expliquant ce qu'il faut faire.
   - **priority** : "haute", "moyenne" ou "basse" selon l'urgence/importance perçue.
3. Ignore les digressions, hésitations et répétitions.
4. Renvoie la liste au format JSON strict correspondant au schéma fourni.

Si aucune tâche n'est identifiable, renvoie une liste vide.
"""


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
        model=VOXTRAL_MODEL,
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


# ---------------------------------------------------------------------------
# 2. Task extraction via Mistral Small + structured JSON
# ---------------------------------------------------------------------------
async def extract_tasks(transcript: str) -> list[TaskItem]:
    """Extract actionable tasks from a transcript using Mistral Small.

    Uses response_format=json_schema with the TaskItem Pydantic schema
    to guarantee structured output.
    """
    client = _get_client()

    # Build the JSON schema for the expected response
    tasks_schema = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": TaskItem.model_json_schema(),
                "description": "List of extracted tasks",
            }
        },
        "required": ["tasks"],
    }

    logger.info("Extracting tasks from transcript (%d chars)…", len(transcript))

    response = await client.chat.complete_async(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Voici la transcription du braindump :\n\n{transcript}",
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "task_list",
                "schema": tasks_schema,
                "strict": True,
            },
        },
        temperature=0.2,
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    # Validate each task through Pydantic
    tasks = [TaskItem.model_validate(t) for t in data.get("tasks", [])]
    logger.info("Extracted %d task(s)", len(tasks))
    return tasks
