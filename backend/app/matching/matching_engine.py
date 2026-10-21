"""Pure profile preparation and matching score orchestration."""
from dataclasses import dataclass
from typing import Any

from app.ai.embedding_service import EmbeddingService, embedding_service
from app.ai.semantic_matcher import semantic_score_from_vectors
from app.matching.education_matcher import education_score
from app.matching.experience_matcher import experience_score
from app.matching.project_matcher import project_score
from app.matching.score_calculator import calculate_overall_score
from app.matching.skill_matcher import calculate_skill_score, job_skill_names, resume_skill_names


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_lines(values: list[Any], limit: int = 24) -> list[str]:
    lines = []
    for value in values[:limit]:
        if isinstance(value, str) and value.strip(): lines.append(value.strip())
        elif isinstance(value, dict):
            lines.append(" ".join(str(value.get(key) or "") for key in ("job_title", "degree", "field_of_study", "description", "institution") if value.get(key)).strip())
    return [line for line in lines if line]


def _education_lines(value: Any) -> list[str]:
    if isinstance(value, str): return [value]
    if isinstance(value, list): return [text for item in value for text in _education_lines(item)]
    if isinstance(value, dict):
        keys = ("degree", "field_of_study", "degree_level", "degrees", "fields")
        return [text for key in keys for text in _education_lines(value.get(key))]
    return []


def build_resume_representation(profile: dict[str, Any]) -> str:
    sections: list[str] = []
    def add(label: str, values: list[str]) -> None:
        if values:
            sections.append(label + ": " + "; ".join(values))
    summary = profile.get("summary")
    if isinstance(summary, str) and summary.strip(): add("Summary", [summary.strip()[:1800]])
    skills = resume_skill_names(profile.get("skills_json"))
    add("Skills", skills[:100])
    add("Experience", _clean_lines(_list(profile.get("experience_json")), 18))
    projects = _list(profile.get("projects_json"))
    project_texts = []
    for project in projects[:20]:
        if isinstance(project, dict):
            value = " ".join(str(project.get(key) or "") for key in ("project_name", "role", "description", "technologies") if project.get(key)).strip()
            if value: project_texts.append(value[:600])
    add("Projects", project_texts)
    add("Education", _education_lines(profile.get("education_json"))[:10])
    return "\n".join(sections)[:7000]


def build_job_representation(job: dict[str, Any], requirements: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    def add(label: str, values: list[str]) -> None:
        values = [value.strip() for value in values if isinstance(value, str) and value.strip()]
        if values: sections.append(label + ": " + "; ".join(values))
    summary = job.get("summary")
    if isinstance(summary, str) and summary.strip(): add("Summary", [summary[:1600]])
    else:
        description = job.get("cleaned_description") or job.get("description")
        if isinstance(description, str) and description.strip(): add("Role description", [description[:1600]])
    add("Responsibilities", _clean_lines(_list(job.get("responsibilities")), 24))
    required = job_skill_names(requirements, "required")
    preferred = job_skill_names(requirements, "preferred")
    add("Required skills", required)
    add("Preferred skills", preferred)
    education = job.get("education_json")
    if isinstance(education, dict):
        add("Education", _education_lines(education)[:6])
    elif isinstance(job.get("education_requirement"), str):
        add("Education", [job["education_requirement"]])
    exp_min, exp_max = job.get("experience_min"), job.get("experience_max")
    if exp_min is not None or exp_max is not None:
        exp = f"minimum {exp_min} years" if exp_min is not None else ""
        if exp_max is not None: exp += ("; " if exp else "") + f"range up to {exp_max} years"
        add("Experience", [exp])
    return "\n".join(sections)[:7000]


@dataclass(frozen=True)
class PreparedMatch:
    resume_profile: dict[str, Any]
    job: dict[str, Any]
    requirements: list[dict[str, Any]]
    resume_text: str
    job_text: str
    projects: list[dict[str, Any]]
    project_context: str


class MatchingEngine:
    def __init__(self, embeddings: EmbeddingService = embedding_service) -> None:
        self.embeddings = embeddings

    def prepare(self, resume_profile: dict[str, Any], job: dict[str, Any], requirements: list[dict[str, Any]]) -> PreparedMatch:
        req = [row for row in requirements if isinstance(row, dict)]
        resume_text = build_resume_representation(resume_profile)
        job_text = build_job_representation(job, req)
        responsibilities = _clean_lines(_list(job.get("responsibilities")), 24)
        targets = job_skill_names(req)
        context = " ".join(responsibilities + targets)
        return PreparedMatch(resume_profile, job, req, resume_text, job_text, _list(resume_profile.get("projects_json")), context)

    def embedding_texts(self, prepared: PreparedMatch) -> list[str]:
        project_texts = [" ".join(str(project.get(key) or "") for key in ("project_name", "role", "description", "technologies") if project.get(key)).strip() for project in prepared.projects if isinstance(project, dict)]
        return [text for text in (prepared.resume_text, prepared.job_text, prepared.project_context, *project_texts) if text]

    def calculate_prepared(self, prepared: PreparedMatch) -> dict[str, float]:
        resume_vector, job_vector = self.embeddings.encode_texts([prepared.resume_text, prepared.job_text]) if prepared.resume_text and prepared.job_text else ([], [])
        semantic = semantic_score_from_vectors(resume_vector, job_vector) if resume_vector and job_vector else 0.0
        required = job_skill_names(prepared.requirements, "required")
        preferred = job_skill_names(prepared.requirements, "preferred")
        skills = calculate_skill_score(prepared.resume_profile.get("skills_json"), required, preferred).score
        exp = experience_score(prepared.resume_profile.get("years_experience"), prepared.job.get("experience_min"), prepared.job.get("experience_max"))
        education = education_score(prepared.resume_profile.get("education_json"), prepared.job.get("education_json"), prepared.job.get("education_requirement"))
        projects = project_score(prepared.projects, required, preferred, prepared.project_context, {}, self.embeddings)
        scores = {"semantic_score": semantic, "skill_score": skills, "experience_score": exp, "education_score": education, "project_score": projects}
        scores["overall_score"] = calculate_overall_score(scores)
        return scores

    def calculate(self, resume_profile: dict[str, Any], job: dict[str, Any], requirements: list[dict[str, Any]]) -> dict[str, float]:
        prepared = self.prepare(resume_profile, job, requirements)
        self.embeddings.encode_texts(self.embedding_texts(prepared))
        return self.calculate_prepared(prepared)
