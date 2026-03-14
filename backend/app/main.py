"""FastAPI application — Décodeur de Pensées."""

import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.schemas import TaskListResponse
from app.services.mistral_service import transcribe_audio, extract_tasks

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Décodeur de Pensées",
    description="Transforme un braindump audio en liste de tâches grâce à Mistral AI.",
    version="1.0.0",
)

# CORS — permissive for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API route
# ---------------------------------------------------------------------------
ALLOWED_MIME_PREFIXES = ("audio/", "video/webm")  # browsers may send video/webm
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@app.post("/api/process-audio", response_model=TaskListResponse)
async def process_audio(file: UploadFile = File(...)):
    """Receive an audio file, transcribe it, extract tasks, return JSON.

    Pipeline:
    1. Validate the uploaded file (type + size).
    2. Call Voxtral to transcribe the audio.
    3. Call Mistral Small to extract structured tasks.
    4. Return the validated TaskListResponse.
    """
    # --- Validate MIME type ---
    content_type = file.content_type or ""
    if not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=415,
            detail=f"Type de fichier non supporté : {content_type}. "
                   "Envoyez un fichier audio (webm, wav, mp3…).",
        )

    # --- Read & validate size ---
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Le fichier dépasse la taille maximale de 25 Mo.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide.",
        )

    logger.info("Received file %s (%s, %d bytes)", file.filename, content_type, len(file_bytes))

    try:
        # Step 1: Transcribe
        transcript = await transcribe_audio(file_bytes, file.filename or "audio.webm")

        # Step 2: Extract tasks
        tasks = await extract_tasks(transcript)

        return TaskListResponse(transcript=transcript, tasks=tasks)

    except Exception as exc:
        logger.exception("Error processing audio")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement : {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Serve frontend static files
# ---------------------------------------------------------------------------
# Local dev:  backend/app/main.py  → _app_dir = backend/app  → .parent.parent = projet-mistral
# Docker:     /app/app/main.py     → _app_dir = /app/app     → .parent = /app
_app_dir = Path(__file__).resolve().parent
_candidates = [
    _app_dir.parent / "frontend",              # Docker: /app/frontend
    _app_dir.parent.parent / "frontend",       # Local:  projet-mistral/frontend
]
FRONTEND_DIR = next((p for p in _candidates if p.is_dir()), None)

if FRONTEND_DIR:
    logger.info("Serving frontend from %s", FRONTEND_DIR)

    @app.get("/")
    async def serve_index():
        """Serve the frontend index.html."""
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

