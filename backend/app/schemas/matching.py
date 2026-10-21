from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class MatchingResult(BaseModel):
    job_id: UUID
    resume_id: UUID
    candidate_id: UUID
    overall_score: float = Field(ge=0, le=100)
    semantic_score: float = Field(ge=0, le=100)
    skill_score: float = Field(ge=0, le=100)
    experience_score: float = Field(ge=0, le=100)
    education_score: float = Field(ge=0, le=100)
    project_score: float = Field(ge=0, le=100)
    created_at: datetime | None = None


class MatchApplicationRequest(BaseModel):
    resume_id: UUID


class MatchingCandidate(BaseModel):
    job_id: UUID
    resume_id: UUID
    candidate_id: UUID
    created_at: datetime | None = None


class MatchingFailure(BaseModel):
    resume_id: UUID
    candidate_id: UUID
    message: str


class BulkMatchingResponse(BaseModel):
    job_id: UUID
    results: list[MatchingResult]
    failures: list[MatchingFailure]
