"""FastAPI application — Décodeur de Pensées + Interview Chatbot."""

import logging
import json
import json
import logging
from pathlib import Path
import fitz  # PyMuPDF

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.schemas import (
    TaskListResponse,
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewChatRequest,
    InterviewChatResponse,
    InterviewFeedback,
    CoverLetterResponse,
    CoverLetterRevisionRequest,
)
from app.services.mistral_service import transcribe_audio, extract_tasks
from app.services.interview_service import (
    start_interview,
    chat_interview,
    generate_feedback,
)
from app.services.cover_letter_service import (
    generate_cover_letter_text,
    revise_cover_letter_text
)

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
# Interview chatbot routes
# ---------------------------------------------------------------------------

@app.post("/api/interview/start", response_model=InterviewStartResponse)
async def api_interview_start(
    cv_file: UploadFile = File(..., description="Le fichier CV (PDF ou TXT)"),
    job_offer: str = Form(..., description="Le texte de l'offre d'emploi"),
):
    """Start a new interview by providing a CV file and a job offer text."""
    if not job_offer.strip():
        raise HTTPException(status_code=400, detail="L'offre d'emploi est vide.")

    # Validate file size
    file_bytes = await cv_file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier CV trop volumineux.")

    # Extract text from CV using the generic helper
    cv_text = await _extract_text_from_upload(cv_file)
    
    if not cv_text:
        raise HTTPException(status_code=400, detail="Le CV est vide.")

    try:
        system_context, first_question = await start_interview(cv_text, job_offer)
        return InterviewStartResponse(
            system_context=system_context,
            first_question=first_question,
            extracted_cv_text=cv_text,
        )
    except Exception as exc:
        logger.exception("Error starting interview")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/interview/chat", response_model=InterviewChatResponse)
async def api_interview_chat(body: InterviewChatRequest):
    """Send a text message and get the recruiter's next question."""
    if not body.messages:
        raise HTTPException(status_code=400, detail="L'historique est vide.")

    try:
        return await chat_interview(body.cv_text, body.job_offer, body.messages)
    except Exception as exc:
        logger.exception("Error in interview chat")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/interview/chat/audio", response_model=InterviewChatResponse)
async def api_interview_chat_audio(
    file: UploadFile = File(...),
    context: str = Form(..., description="JSON InterviewChatRequest string"),
):
    """Send an audio response, transcribe it, and get the recruiter's next question."""
    # Parse the context JSON (cv_text, job_offer, messages)
    try:
        ctx_data = json.loads(context)
        chat_req = InterviewChatRequest.model_validate(ctx_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Contexte JSON invalide : {exc}")

    # Validate audio file
    content_type = file.content_type or ""
    if not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=415,
            detail=f"Type de fichier non supporté : {content_type}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")

    try:
        # 1. Transcribe the audio
        logger.info("Transcribing interview audio response...")
        transcript = await transcribe_audio(file_bytes, file.filename or "audio.webm")
        if not transcript.strip():
            transcript = "(audio inaudible)"

        # 2. Add the transcribed text as a user message
        from app.schemas import ChatMessage
        chat_req.messages.append(ChatMessage(role="user", content=transcript))

        # 3. Get recruiter reply
        chat_res = await chat_interview(
            chat_req.cv_text, chat_req.job_offer, chat_req.messages
        )

        # 4. Attach transcript to response
        # We need to manually construct it since we are adding the transcript
        return InterviewChatResponse(
            user_transcript=transcript,
            reply=chat_res.reply,
            is_final=chat_res.is_final
        )

    except Exception as exc:
        logger.exception("Error in interview audio chat")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/interview/feedback", response_model=InterviewFeedback)
async def api_interview_feedback(body: InterviewChatRequest):
    """Generate a structured feedback report after the interview."""
    if len(body.messages) < 2:
        raise HTTPException(
            status_code=400,
            detail="Il faut au moins un échange pour générer le feedback.",
        )

    try:
        return await generate_feedback(body.cv_text, body.job_offer, body.messages)
    except Exception as exc:
        logger.exception("Error generating feedback")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# API Routes: Cover Letter Generator
# ---------------------------------------------------------------------------

import io
import docx

async def _extract_text_from_upload(upload_file: UploadFile) -> str:
    """Helper purely to abstract PyMuPDF/docx/text extraction."""
    file_bytes = await upload_file.read()
    if len(file_bytes) == 0:
        return ""
    
    content_type = upload_file.content_type or ""
    filename = upload_file.filename.lower() if upload_file.filename else ""
    text = ""
    
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text()
        except Exception as exc:
            logger.error(f"Erreur d'extraction d'un PDF: {exc}")
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.endswith(".docx"):
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as exc:
            logger.error(f"Erreur d'extraction d'un fichier DOCX: {exc}")
    else:
        try:
            text = file_bytes.decode("utf-8")
        except Exception:
            text = "" # Ignore non-decodable files instead of throwing if they are optional
    return text.strip()

@app.post("/api/cover-letter/generate", response_model=CoverLetterResponse)
async def api_cover_letter_generate(
    job_offer: str = Form(..., description="Le texte de l'offre d'emploi"),
    language: str = Form("français", description="Langue de la lettre (français ou anglais)"),
    cv_file: UploadFile = File(..., description="Le fichier CV (PDF ou TXT)"),
    example_files: list[UploadFile] = File(default=None, description="Fichiers PDF/TXT facultatifs servant d'exemples de style"),
):
    """Generate a tailored cover letter from CV, Job Offer and optional examples."""
    if not job_offer.strip():
        raise HTTPException(status_code=400, detail="L'offre d'emploi est vide.")

    # 1) Extract CV Text
    cv_text = await _extract_text_from_upload(cv_file)
    if not cv_text:
        raise HTTPException(status_code=400, detail="Impossible de lire le contenu du CV.")

    # 2) Extract Examples Text
    extracted_examples = []
    if example_files:
        for ex_file in example_files:
            if ex_file.filename:  # Avoid empty file inputs
                ex_text = await _extract_text_from_upload(ex_file)
                if ex_text:
                    extracted_examples.append(ex_text)

    # 3) Call AI Service
    try:
        return await generate_cover_letter_text(cv_text, job_offer, language, extracted_examples)
    except Exception as exc:
        logger.exception("Error generating cover letter")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/api/cover-letter/revise", response_model=CoverLetterResponse)
async def api_cover_letter_revise(request: CoverLetterRevisionRequest):
    """Revise an existing cover letter based on user instructions."""
    if not request.current_letter.strip():
        raise HTTPException(status_code=400, detail="La lettre actuelle est vide.")
    if not request.instructions.strip():
        raise HTTPException(status_code=400, detail="Les instructions sont vides.")
        
    try:
        return await revise_cover_letter_text(
            current_letter=request.current_letter,
            instructions=request.instructions,
            language=request.language
        )
    except Exception as exc:
        logger.exception("Error revising cover letter")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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

    @app.get("/interview")
    async def serve_interview():
        """Serve the interview chatbot page."""
        return FileResponse(FRONTEND_DIR / "interview.html")

    @app.get("/coverletter")
    async def serve_cover_letter():
        """Serve the cover letter generator page."""
        return FileResponse(FRONTEND_DIR / "coverletter.html")

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

