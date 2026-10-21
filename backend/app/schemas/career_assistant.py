from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CareerAssistantSessionInput(BaseModel):
    session_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=4000)
    session_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CareerAssistantResponse(BaseModel):
    response: str
    session_id: UUID | None = None
    message_id: UUID | None = None


class CareerAssistantSession(BaseModel):
    id: UUID
    candidate_id: UUID
    title: str | None = None
    session_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None


class CareerAssistantMessage(BaseModel):
    id: UUID
    session_id: UUID
    candidate_id: UUID
    role: Literal['user', 'assistant', 'system']
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ResumeReviewRequest(BaseModel):
    resume_id: UUID | None = None
    include_summary: bool = True


class SkillGapRequest(BaseModel):
    job_id: UUID | None = None
    job_description: str | None = None
    target_role: str | None = None


class InterviewRequest(BaseModel):
    interview_type: Literal['general', 'technical', 'behavioral', 'job_specific'] = 'general'
    job_id: UUID | None = None
    job_description: str | None = None
    target_role: str | None = None
