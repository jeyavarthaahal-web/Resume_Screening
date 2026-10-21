from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NoteInput(BaseModel):
    job_id: UUID
    note: str = Field(min_length=1, max_length=5000)


class NoteUpdate(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class CompareInput(BaseModel):
    job_id: UUID
    candidate_ids: list[UUID] = Field(min_length=2, max_length=5)


class CandidatePage(BaseModel):
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    required_skills: list[str] = []
