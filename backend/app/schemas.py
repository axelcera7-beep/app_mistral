"""Pydantic models for structured task extraction."""

from pydantic import BaseModel, Field
from typing import Literal


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
