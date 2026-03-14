"""Pydantic models for structured task extraction and interview chatbot."""

from pydantic import BaseModel, Field
from typing import Literal


# ---------------------------------------------------------------------------
# Braindump — Task extraction
# ---------------------------------------------------------------------------

class TaskItem(BaseModel):
    """A single actionable task extracted from the braindump."""

    title: str = Field(description="Short, actionable title for the task")
    description: str = Field(description="Brief description of what needs to be done")
    priority: Literal["haute", "moyenne", "basse"] = Field(
        description="Priority level of the task"
    )


class TaskListResponse(BaseModel):
    """Response containing the transcript and extracted tasks."""

    transcript: str = Field(description="Raw transcript of the audio")
    tasks: list[TaskItem] = Field(description="List of extracted tasks")


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


# --- Responses ---

class InterviewStartResponse(BaseModel):
    """Response when starting a new interview."""

    system_context: str = Field(description="Summary of CV + offer for frontend context")
    first_question: str = Field(description="First interview question from the recruiter")
    extracted_cv_text: str = Field(description="The parsed CV text so the frontend can send it back")


class InterviewChatResponse(BaseModel):
    """Response for each chat turn."""

    user_transcript: str | None = Field(
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
    summary: str = Field(description="A brief explanation of the choices made")

class CoverLetterRevisionRequest(BaseModel):
    """Data required to revise an existing cover letter."""
    
    current_letter: str = Field(description="The cover letter text as it currently is")
    instructions: str = Field(description="What the user wants to change (e.g., 'Make it shorter', 'Tone down the enthusiasm')")
    language: str = Field(default="français", description="Language of the generated cover letter")

