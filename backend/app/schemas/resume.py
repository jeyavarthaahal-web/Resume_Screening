"""Typed request/response models for resume intelligence."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EducationItem(BaseModel):
    degree: str | None = None
    field_of_study: str | None = None
    institution: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ExperienceItem(BaseModel):
    job_title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class Skills(BaseModel):
    technical: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    project_name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    role: str | None = None
    url: str | None = None


class CertificationItem(BaseModel):
    certification_name: str
    issuer: str | None = None
    date: str | None = None
    credential_id: str | None = None


class AchievementItem(BaseModel):
    title: str
    description: str | None = None


class LanguageItem(BaseModel):
    name: str
    proficiency: str | None = None


class DetectedSections(BaseModel):
    summary: bool = False
    education: bool = False
    experience: bool = False
    skills: bool = False
    projects: bool = False
    certifications: bool = False
    achievements: bool = False
    languages: bool = False
    other: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    years_experience: float | None = None
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    achievements: list[AchievementItem] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)
    sections: DetectedSections = Field(default_factory=DetectedSections)


class ParserMetadata(BaseModel):
    page_count: int | None = None
    document_metadata: dict[str, Any] = Field(default_factory=dict)


class ResumeRecord(BaseModel):
    id: UUID
    candidate_id: UUID
    file_name: str
    file_type: str
    file_size: int
    status: Literal['processed']
    created_at: datetime

    model_config = ConfigDict(extra='ignore')


class ResumeUploadResponse(BaseModel):
    status: Literal['processed']
    resume: ResumeRecord
    profile: ResumeProfile
    parser: ParserMetadata
