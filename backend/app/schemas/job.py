from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class JobRequirement(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    original_name: str | None = None
    category: str | None = None
    importance: Literal["required", "preferred"] = "preferred"

class EducationRequirement(BaseModel):
    degree_level: str | None = None
    degrees: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)

class ExperienceRequirement(BaseModel):
    minimum: float | None = Field(default=None, ge=0, le=80)
    maximum: float | None = Field(default=None, ge=0, le=80)

    @model_validator(mode="after")
    def range_is_valid(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Minimum experience cannot exceed maximum experience.")
        return self

class JobStructuredProfile(BaseModel):
    job_title: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    work_mode: Literal["Remote", "Hybrid", "On-site"] | None = None
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[JobRequirement] = Field(default_factory=list)
    preferred_skills: list[JobRequirement] = Field(default_factory=list)
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud_platforms: list[str] = Field(default_factory=list)
    minimum_experience: float | None = Field(default=None, ge=0, le=80)
    maximum_experience: float | None = Field(default=None, ge=0, le=80)
    education_requirement: EducationRequirement | None = None
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    raw_description: str | None = None
    cleaned_description: str | None = None
    classification_note: str | None = None

    @model_validator(mode="after")
    def valid_experience_range(self):
        if self.minimum_experience is not None and self.maximum_experience is not None and self.minimum_experience > self.maximum_experience:
            raise ValueError("Minimum experience cannot exceed maximum experience.")
        return self

class JobAnalysisResponse(JobStructuredProfile):
    analysis_status: Literal["analyzed"] = "analyzed"

class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str | None = Field(default=None, max_length=160)
    description: str = Field(min_length=40, max_length=50000)
    location: str | None = Field(default=None, max_length=200)
    employment_type: Literal["full_time", "part_time", "contract", "temporary", "internship", "other"] | None = None
    work_mode: Literal["Remote", "Hybrid", "On-site"] | None = None
    experience_min: float | None = Field(default=None, ge=0, le=80)
    experience_max: float | None = Field(default=None, ge=0, le=80)
    education_requirement: str | None = None
    status: Literal["draft", "published"] = "draft"
    profile: JobStructuredProfile | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip(): raise ValueError("Job title cannot be blank.")
        return value.strip()

    @field_validator("description")
    @classmethod
    def description_has_content(cls, value: str) -> str:
        if len(value.strip()) < 40:
            raise ValueError("Add a little more detail to the job description before saving it.")
        return value

    @model_validator(mode="after")
    def valid_range(self):
        if self.experience_min is not None and self.experience_max is not None and self.experience_min > self.experience_max:
            raise ValueError("Minimum experience cannot exceed maximum experience.")
        return self

class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    department: str | None = None
    description: str | None = Field(default=None, min_length=40, max_length=50000)
    location: str | None = None
    employment_type: Literal["full_time", "part_time", "contract", "temporary", "internship", "other"] | None = None
    work_mode: Literal["Remote", "Hybrid", "On-site"] | None = None
    experience_min: float | None = Field(default=None, ge=0, le=80)
    experience_max: float | None = Field(default=None, ge=0, le=80)
    education_requirement: str | None = None
    status: Literal["draft", "published", "closed"] | None = None

    @model_validator(mode="after")
    def valid_experience_range(self):
        if self.experience_min is not None and self.experience_max is not None and self.experience_min > self.experience_max:
            raise ValueError("Minimum experience cannot exceed maximum experience.")
        return self

class JobResponse(BaseModel):
    id: UUID
    recruiter_id: UUID
    title: str
    department: str | None = None
    description: str
    location: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    experience_min: float | None = None
    experience_max: float | None = None
    education_requirement: str | None = None
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    education_json: dict[str, Any] | None = None
    certifications_json: list[dict[str, Any]] = Field(default_factory=list)
    benefits_json: list[str] = Field(default_factory=list)
    analysis_status: str = "pending"
    status: str
    requirements: list[JobRequirement] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(extra="ignore")
