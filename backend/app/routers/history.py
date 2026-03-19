"""History routes — extracted from main.py without modification."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, CoverLetterHistory, InterviewReport, SavedJob

from app.schemas import (
    CoverLetterHistoryItem,
    CoverLetterDetail,
    InterviewReportItem,
    InterviewReportDetail,
    FeedbackPoint,
    VisualAnalysisReport,
    SavedJobItem,
    SavedJobDetail,
)


from app.services.auth_service import get_current_user

router = APIRouter()


# --- Cover Letters History ---


@router.get("/api/cover-letters", response_model=list[CoverLetterHistoryItem])
def api_cover_letters_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List saved cover letters for the current user (paginated)."""
    letters = (
        db.query(CoverLetterHistory)
        .filter(CoverLetterHistory.user_id == user.id)
        .order_by(CoverLetterHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return letters


@router.get("/api/cover-letters/{letter_id}", response_model=CoverLetterDetail)
def api_cover_letter_detail(
    letter_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full detail of a saved cover letter."""
    letter = (
        db.query(CoverLetterHistory)
        .filter(CoverLetterHistory.id == letter_id, CoverLetterHistory.user_id == user.id)
        .first()
    )
    if not letter:
        raise HTTPException(status_code=404, detail="Lettre introuvable.")
    return letter


@router.delete("/api/cover-letters/{letter_id}")
def api_cover_letter_delete(
    letter_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved cover letter."""
    letter = (
        db.query(CoverLetterHistory)
        .filter(CoverLetterHistory.id == letter_id, CoverLetterHistory.user_id == user.id)
        .first()
    )
    if not letter:
        raise HTTPException(status_code=404, detail="Lettre introuvable.")
    db.delete(letter)
    db.commit()
    return {"detail": "Supprimée."}


# --- Interview Reports History ---


@router.get("/api/interviews", response_model=list[InterviewReportItem])
def api_interviews_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List saved interview reports for the current user (paginated)."""
    reports = (
        db.query(InterviewReport)
        .filter(InterviewReport.user_id == user.id)
        .order_by(InterviewReport.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return reports


@router.get("/api/interviews/{report_id}", response_model=InterviewReportDetail)
def api_interview_detail(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full detail of a saved interview report."""
    report = (
        db.query(InterviewReport)
        .filter(InterviewReport.id == report_id, InterviewReport.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable.")
    # Parse JSON fields into Pydantic models
    return InterviewReportDetail(
        id=report.id,
        title=report.title,
        job_offer_snippet=report.job_offer_snippet,
        score=report.score,
        summary=report.summary,
        strengths=[FeedbackPoint(**s) for s in report.strengths],
        improvements=[FeedbackPoint(**i) for i in report.improvements],
        advice=report.advice,
        visual_report=VisualAnalysisReport.model_validate(report.visual_report) if report.visual_report else None,
        created_at=report.created_at,
    )


@router.delete("/api/interviews/{report_id}")
def api_interview_delete(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved interview report."""
    report = (
        db.query(InterviewReport)
        .filter(InterviewReport.id == report_id, InterviewReport.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable.")
    db.delete(report)
    db.commit()
    return {"detail": "Supprimé."}


# --- Saved Jobs History ---


@router.get("/api/jobs/saved", response_model=list[SavedJobItem])
def api_saved_jobs_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List saved job offers for the current user (paginated)."""
    jobs = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == user.id)
        .order_by(SavedJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jobs


@router.get("/api/jobs/saved/{job_id}", response_model=SavedJobDetail)
def api_saved_job_detail(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full detail of a saved job offer."""
    job = (
        db.query(SavedJob)
        .filter(SavedJob.id == job_id, SavedJob.user_id == user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Offre introuvable.")
    return job


@router.delete("/api/jobs/saved/{job_id}")
def api_saved_job_delete(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved job offer."""
    job = (
        db.query(SavedJob)
        .filter(SavedJob.id == job_id, SavedJob.user_id == user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Offre introuvable.")
    db.delete(job)
    db.commit()
    return {"detail": "Supprimée."}

