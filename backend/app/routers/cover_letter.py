"""Cover letter routes — extracted from main.py without modification."""

import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, CoverLetterHistory
from app.schemas import CoverLetterResponse, CoverLetterRevisionRequest
from app.services.cover_letter_service import (
    generate_cover_letter_text,
    revise_cover_letter_text,
)
from app.services.auth_service import get_optional_user
from app.utils import extract_text_from_upload, make_offer_snippet

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/cover-letter/generate", response_model=CoverLetterResponse)
async def api_cover_letter_generate(
    job_offer: str = Form(..., description="Le texte de l'offre d'emploi"),
    language: str = Form("français", description="Langue de la lettre"),
    cv_file: UploadFile = File(..., description="Le fichier CV (PDF ou TXT)"),
    example_files: list[UploadFile] = File(default=None, description="Fichiers exemples"),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Generate a tailored cover letter. Saves to DB if user is authenticated."""
    if not job_offer.strip():
        raise HTTPException(status_code=400, detail="L'offre d'emploi est vide.")

    cv_text = await extract_text_from_upload(cv_file)
    if not cv_text:
        raise HTTPException(status_code=400, detail="Impossible de lire le contenu du CV.")

    extracted_examples = []
    if example_files:
        for ex_file in example_files:
            if ex_file.filename:
                ex_text = await extract_text_from_upload(ex_file)
                if ex_text:
                    extracted_examples.append(ex_text)

    try:
        result = await generate_cover_letter_text(cv_text, job_offer, language, extracted_examples)

        # Save to database if user is authenticated
        if user:
            record = CoverLetterHistory(
                user_id=user.id,
                job_offer_snippet=make_offer_snippet(job_offer),
                letter_body=result.letter_body,
                summary=result.summary,
                language=language,
            )
            db.add(record)
            db.commit()
            logger.info("Cover letter saved for user %s", user.username)

        return result
    except Exception as exc:
        logger.exception("Error generating cover letter")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/cover-letter/revise", response_model=CoverLetterResponse)
async def api_cover_letter_revise(
    request: CoverLetterRevisionRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Revise an existing cover letter based on user instructions. Saves to DB if authenticated."""
    if not request.current_letter.strip():
        raise HTTPException(status_code=400, detail="La lettre actuelle est vide.")
    if not request.instructions.strip():
        raise HTTPException(status_code=400, detail="Les instructions sont vides.")

    try:
        result = await revise_cover_letter_text(
            current_letter=request.current_letter,
            instructions=request.instructions,
            language=request.language,
        )

        if user:
            record = CoverLetterHistory(
                user_id=user.id,
                job_offer_snippet=make_offer_snippet(request.job_offer) if request.job_offer else "Révision",
                letter_body=result.letter_body,
                summary=result.summary,
                language=request.language,
            )
            db.add(record)
            db.commit()
            logger.info("Revised cover letter saved for user %s", user.username)

        return result
    except Exception as exc:
        logger.exception("Error revising cover letter")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
