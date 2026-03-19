"""Job search and save routes."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SavedJob, User
from app.schemas import JobSearchResponse, SavedJobRequest
from app.services.auth_service import get_current_user
from app.services.job_service import match_jobs_with_cv, search_jobs_all
from app.utils import extract_text_from_upload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["jobs"])


@router.post("/api/jobs/search", response_model=JobSearchResponse)
async def search_jobs(
    keywords: str = Form(...),
    location: str = Form(""),
    cv_text: Optional[str] = Form(None),
    cv_file: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search for jobs and calculate matching scores if a CV is provided."""
    logger.info("User %s searching: keywords=%s, location=%s", user.username, keywords, location)

    # 1. Resolve CV text (file upload takes priority over raw text)
    final_cv_text = cv_text
    if cv_file:
        try:
            extracted = await extract_text_from_upload(cv_file)
            if extracted:
                final_cv_text = extracted
        except Exception:
            logger.exception("Failed to extract text from %s", cv_file.filename)

    # 2. Fetch jobs from all sources (JSearch + Adzuna)
    try:
        jobs = await search_jobs_all(keywords, location)
    except Exception:
        logger.exception("Job search failed")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des offres.")

    if not jobs:
        logger.info("No jobs found for keywords=%s, location=%s", keywords, location)
        return JobSearchResponse(results=[], count=0)

    # 3. Smart matching if CV is available
    if final_cv_text:
        logger.info("Calculating CV matching scores...")
        try:
            jobs = await match_jobs_with_cv(final_cv_text, jobs)
        except Exception:
            logger.exception("Job matching failed — returning unranked results")

    return JobSearchResponse(results=jobs, count=len(jobs))


@router.post("/api/jobs/save")
async def api_save_job(
    request: SavedJobRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a job offer to the user's history."""
    existing = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == user.id, SavedJob.external_id == request.external_id)
        .first()
    )
    if existing:
        return {"detail": "Déjà sauvegardée."}

    saved_job = SavedJob(
        user_id=user.id,
        external_id=request.external_id,
        title=request.title,
        company=request.company,
        location=request.location,
        description=request.description,
        salary=request.salary,
        redirect_url=request.redirect_url,
    )
    db.add(saved_job)
    db.commit()
    db.refresh(saved_job)

    logger.info("Job saved for user %s: %s", user.username, request.title)
    return {"detail": "Offre sauvegardée !", "id": saved_job.id}
