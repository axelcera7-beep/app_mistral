"""Pydantic models for structured task extraction, interview chatbot, cover letter, and auth."""

from datetime import datetime
from typing import Literal, Optional, List

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Visual Analysis (webcam)
# ---------------------------------------------------------------------------

class VisualObservation(BaseModel):
    """A single visual observation from the webcam analysis."""

    category: str = Field(description="Category: expressions_faciales, posture, contact_visuel, confiance_generale")
    observation: str = Field(description="What was observed")
    assessment: Literal["positif", "neutre", "à améliorer"] = Field(description="Assessment level")


class VisualAnalysisReport(BaseModel):
    """Report from webcam visual analysis during an interview."""

    overall_impression: str = Field(description="Overall impression of the candidate's body language")
    confidence_score: int = Field(ge=0, le=10, description="Confidence level score out of 10")
    observations: list[VisualObservation] = Field(description="Detailed observations by category")
    recommendations: list[str] = Field(description="List of actionable improvement suggestions")


class VisualAnalysisRequest(BaseModel):
    """Request body for visual analysis endpoint."""

    frames: list[str] = Field(description="List of base64-encoded JPEG frames from the webcam")
    job_offer: str = Field(default="", description="Job offer context for tailored analysis")


# ---------------------------------------------------------------------------
# Interview chatbot
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single message in the interview conversation."""

    role: Literal["user", "assistant"] = Field(description="Who sent this message")
    content: str = Field(description="Message content")


# --- Requests ---

class InterviewStartRequest(BaseModel):
    """Payload to start a new mock interview."""

    cv_text: str = Field(description="Full text content of the candidate's CV")
    job_offer: str = Field(description="Full text of the job/internship offer")


class InterviewChatRequest(BaseModel):
    """Payload for a follow-up chat turn during the interview."""

    cv_text: str = Field(description="Full text content of the candidate's CV")
    job_offer: str = Field(description="Full text of the job/internship offer")
    messages: list[ChatMessage] = Field(description="Full conversation history so far")
    visual_report: Optional[VisualAnalysisReport] = Field(
        default=None, description="Visual assessment from webcam if available"
    )


# --- Responses ---

class InterviewStartResponse(BaseModel):
    """Response when starting a new interview."""

    system_context: str = Field(description="Summary of CV + offer for frontend context")
    first_question: str = Field(description="First interview question from the recruiter")
    extracted_cv_text: str = Field(description="The parsed CV text so the frontend can send it back")


class InterviewChatResponse(BaseModel):
    """Response for each chat turn."""

    user_transcript: Optional[str] = Field(
        default=None, description="Transcribed audio text if voice mode was used"
    )
    reply: str = Field(description="Recruiter's question or follow-up")
    is_final: bool = Field(
        default=False,
        description="True when the recruiter considers the interview complete",
    )


class FeedbackPoint(BaseModel):
    """A single evaluation point in the interview feedback."""

    topic: str = Field(description="Topic assessed (e.g. 'Motivation', 'Technical skills')")
    assessment: Literal["fort", "à améliorer"] = Field(description="Overall assessment")
    comment: str = Field(description="Detailed comment for this topic")


class InterviewFeedback(BaseModel):
    """Structured post-interview feedback report."""

    summary: str = Field(description="Overall performance summary")
    score: int = Field(ge=0, le=10, description="Score out of 10")
    strengths: list[FeedbackPoint] = Field(description="List of strong points")
    improvements: list[FeedbackPoint] = Field(description="List of areas to improve")
    advice: str = Field(description="Key piece of advice for the candidate")
    visual_report: Optional["VisualAnalysisReport"] = Field(
        default=None, description="Visual analysis from webcam if available"
    )


# ===========================================================================
# COVER LETTER GENERATOR SCHEMAS
# ===========================================================================

class CoverLetterRequest(BaseModel):
    """Data required to generate a cover letter."""

    cv_text: str = Field(description="Full text content of the candidate's CV")
    job_offer: str = Field(description="Full text of the job/internship offer")
    language: str = Field(default="français", description="Language of the generated cover letter")
    examples: list[str] = Field(
        default_factory=list,
        description="Optional list of previous cover letters to emulate style"
    )

class CoverLetterResponse(BaseModel):
    """Generated cover letter response."""

    letter_body: str = Field(description="The complete generated cover letter text")
    summary: Optional[str] = Field(default=None, description="A brief explanation of the choices made")

class CoverLetterRevisionRequest(BaseModel):
    """Data required to revise an existing cover letter."""

    current_letter: str = Field(description="The cover letter text as it currently is")
    instructions: str = Field(description="What the user wants to change (e.g., 'Make it shorter', 'Tone down the enthusiasm')")
    language: str = Field(default="français", description="Language of the generated cover letter")
    job_offer: str = Field(default="", description="Original job offer text for history snippet")


# ===========================================================================
# AUTHENTICATION SCHEMAS
# ===========================================================================

class RegisterRequest(BaseModel):
    """Payload for user registration."""
    username: str = Field(min_length=3, max_length=50, description="Nom d'utilisateur unique")
    email: str = Field(description="Adresse email")
    password: str = Field(min_length=6, description="Mot de passe (min 6 caractères)")


class LoginRequest(BaseModel):
    """Payload for user login."""
    username: str = Field(description="Nom d'utilisateur")
    password: str = Field(description="Mot de passe")


class AuthResponse(BaseModel):
    """Response after successful login/registration."""
    token: str = Field(description="JWT access token")
    username: str = Field(description="Nom d'utilisateur")


class UserResponse(BaseModel):
    """Public user information."""
    id: int
    username: str
    email: str


# ===========================================================================
# HISTORY SCHEMAS
# ===========================================================================

class CoverLetterHistoryItem(BaseModel):
    """Summary of a saved cover letter for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_offer_snippet: str
    language: str
    created_at: datetime


class CoverLetterDetail(BaseModel):
    """Full detail of a saved cover letter."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_offer_snippet: str
    letter_body: str
    summary: Optional[str] = None
    language: str
    created_at: datetime


class InterviewReportItem(BaseModel):
    """Summary of a saved interview report for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    score: int
    created_at: datetime


class InterviewReportDetail(BaseModel):
    """Full detail of a saved interview report."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    job_offer_snippet: str
    score: int
    summary: str
    strengths: list[FeedbackPoint]
    improvements: list[FeedbackPoint]
    advice: Optional[str] = None
    visual_report: Optional[VisualAnalysisReport] = None
    created_at: datetime

# ===========================================================================
# JOB SEARCH SCHEMAS
# ===========================================================================

class JobSearchRequest(BaseModel):
    """Payload to search for jobs."""
    keywords: str = Field(description="Search keywords (e.g. 'Software Engineer')")
    location: str = Field(description="Search location (e.g. 'Paris')")
    cv_text: Optional[str] = Field(default=None, description="Candidate CV text for smart matching")

class JobOfferResult(BaseModel):
    """A single job offer result from search."""
    id: str
    title: str
    company: str
    location: str
    description: str
    salary: Optional[str] = None
    redirect_url: str
    match_score: Optional[float] = Field(default=None, description="Similarity score with CV (0-100)")
    created: str

class JobSearchResponse(BaseModel):
    """Response containing a list of job offers."""
    results: List[JobOfferResult] = Field(description="List of found job offers ranked by relevance")
    count: int = Field(description="Total number of results found")


class SavedJobRequest(BaseModel):
    """Payload to save a job offer."""
    external_id: str
    title: str
    company: str
    location: str
    description: str
    salary: Optional[str] = None
    redirect_url: str


class SavedJobItem(BaseModel):
    """Summary of a saved job for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    title: str
    company: str
    location: str
    created_at: datetime


class SavedJobDetail(BaseModel):
    """Full detail of a saved job."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    title: str
    company: str
    location: str
    description: str
    salary: Optional[str] = None
    redirect_url: str
    created_at: datetime

