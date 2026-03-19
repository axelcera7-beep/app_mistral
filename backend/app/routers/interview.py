"""Interview chatbot routes — extracted from main.py without modification."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InterviewReport, User
from app.schemas import (
    ChatMessage,
    InterviewChatRequest,
    InterviewChatResponse,
    InterviewFeedback,
    InterviewStartResponse,
    VisualAnalysisReport,
    VisualAnalysisRequest,
)
from app.services.auth_service import get_optional_user
from app.services.interview_service import chat_interview, generate_feedback, start_interview
from app.services.vision_service import analyze_visual
from app.services.voice_service import transcribe_audio
from app.utils import ALLOWED_MIME_PREFIXES, MAX_FILE_SIZE, extract_text_from_upload

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/interview/start", response_model=InterviewStartResponse)
async def api_interview_start(
    cv_file: UploadFile = File(..., description="Le fichier CV (PDF ou TXT)"),
    job_offer: str = Form(..., description="Le texte de l'offre d'emploi"),
):
    """Start a new interview by providing a CV file and a job offer text."""
    if not job_offer.strip():
        raise HTTPException(status_code=400, detail="L'offre d'emploi est vide.")

    file_bytes = await cv_file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier CV trop volumineux.")

    cv_text = await extract_text_from_upload(cv_file)
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


@router.post("/api/interview/chat", response_model=InterviewChatResponse)
async def api_interview_chat(body: InterviewChatRequest):
    """Send a text message and get the recruiter's next question."""
    if not body.messages:
        raise HTTPException(status_code=400, detail="L'historique est vide.")

    try:
        return await chat_interview(body.cv_text, body.job_offer, body.messages)
    except Exception as exc:
        logger.exception("Error in interview chat")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/interview/chat/audio", response_model=InterviewChatResponse)
async def api_interview_chat_audio(
    file: UploadFile = File(...),
    context: str = Form(..., description="JSON InterviewChatRequest string"),
):
    """Send an audio response, transcribe it, and get the recruiter's next question."""
    try:
        ctx_data = json.loads(context)
        chat_req = InterviewChatRequest.model_validate(ctx_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Contexte JSON invalide : {exc}")

    content_type = file.content_type or ""
    if not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=415, detail=f"Type de fichier non supporté : {content_type}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")

    try:
        logger.info("Transcribing interview audio response...")
        transcript = await transcribe_audio(file_bytes, file.filename or "audio.webm")
        if not transcript.strip():
            transcript = "(audio inaudible)"

        chat_req.messages.append(ChatMessage(role="user", content=transcript))

        chat_res = await chat_interview(
            chat_req.cv_text, chat_req.job_offer, chat_req.messages
        )

        return InterviewChatResponse(
            user_transcript=transcript,
            reply=chat_res.reply,
            is_final=chat_res.is_final,
        )
    except Exception as exc:
        logger.exception("Error in interview audio chat")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/interview/visual-analysis", response_model=VisualAnalysisReport)
async def api_interview_visual_analysis(body: VisualAnalysisRequest):
    """Analyze webcam frames and return a visual body language report."""
    if not body.frames:
        raise HTTPException(status_code=400, detail="Aucune image fournie.")
    if len(body.frames) > 20:
        raise HTTPException(status_code=400, detail="Trop d'images (max 20).")

    try:
        report = await analyze_visual(body.frames, body.job_offer)
        return report
    except Exception as exc:
        logger.exception("Error in visual analysis")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/interview/feedback", response_model=InterviewFeedback)
async def api_interview_feedback(
    body: InterviewChatRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Generate a structured feedback report after the interview.
    If a user is authenticated, saves the report to the database.
    """
    if len(body.messages) < 2:
        raise HTTPException(
            status_code=400,
            detail="Il faut au moins un échange pour générer le feedback.",
        )

    try:
        feedback = await generate_feedback(body.cv_text, body.job_offer, body.messages)

        # Save to database if user is authenticated
        if user:
            report = InterviewReport(
                user_id=user.id,
                title=f"Entretien - {body.job_offer[:30]}...",
                job_offer_snippet=body.job_offer[:200],
                summary=feedback.summary,
                score=feedback.score,
                strengths=[p.model_dump() for p in feedback.strengths],
                improvements=[p.model_dump() for p in feedback.improvements],
                advice=feedback.advice,
                visual_report=body.visual_report.model_dump() if body.visual_report else None,
            )
            db.add(report)
            db.commit()
            logger.info("Interview report saved for user %s", user.username)

        # If we had a visual report in the request, add it to the response so it shows up in UI
        if body.visual_report:
            feedback.visual_report = body.visual_report

        return feedback
    except Exception as exc:
        logger.exception("Error generating feedback")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
