"""API contracts for traceable Task 7 explanations."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Importance = Literal["required", "preferred"]
SkillStatus = Literal["matched", "partial", "missing"]
EvidenceType = Literal["skill", "experience", "education", "project", "summary", "responsibility"]


class Evidence(BaseModel):
    type: EvidenceType
    source: Literal["resume", "job"]
    text: str = Field(max_length=300)
    related_requirement: str | None = None


class SkillClassification(BaseModel):
    name: str
    importance: Importance
    status: SkillStatus
    resume_skill: str | None = None


class ScoreComponent(BaseModel):
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    weighted_contribution: float = Field(ge=0, le=100)


class Strength(BaseModel):
    title: str
    description: str
    evidence: list[Evidence]


class Gap(BaseModel):
    title: str
    description: str
    severity: Literal["required", "preferred", "informational"]
    status: Literal["missing", "partial", "below_requirement", "not_identified"]
    evidence: list[Evidence] = Field(default_factory=list)


class ExperienceContext(BaseModel):
    candidate_years: float | None = None
    minimum_years: float | None = None
    maximum_years: float | None = None
    status: Literal["matched", "below_requirement", "maximum_only", "not_specified", "not_identified"]


class EducationContext(BaseModel):
    candidate: list[str] = Field(default_factory=list)
    requirement: list[str] = Field(default_factory=list)
    status: Literal["matched", "partial", "not_specified", "not_identified"]


class RelevantProject(BaseModel):
    project_name: str
    relevant_technologies: list[str]
    related_job_requirements: list[str]
    evidence: Evidence


class RankingExplanation(BaseModel):
    job_id: UUID
    resume_id: UUID
    candidate_id: UUID
    overall_score: float = Field(ge=0, le=100)
    score_breakdown: dict[str, ScoreComponent]
    matched_skills: list[SkillClassification]
    partial_skills: list[SkillClassification]
    missing_skills: list[SkillClassification]
    strengths: list[Strength]
    gaps: list[Gap]
    evidence: list[Evidence]
    explanation: str
    experience_context: ExperienceContext
    education_context: EducationContext
    relevant_projects: list[RelevantProject]
    data_quality: Literal["complete", "partially_complete", "limited"]
    data_quality_note: str
    generated_at: datetime | None = None


class RankingFailure(BaseModel):
    resume_id: UUID
    candidate_id: UUID
    message: str


class BulkRankingExplanation(BaseModel):
    job_id: UUID
    results: list[RankingExplanation]
    failures: list[RankingFailure]
