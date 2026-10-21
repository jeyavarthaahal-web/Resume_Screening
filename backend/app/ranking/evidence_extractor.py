"""Extract short, verbatim evidence snippets from structured source fields."""
from typing import Any

from app.schemas.ranking import Evidence


def _compact(value: Any, limit: int = 240) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def extract_evidence(profile: dict[str, Any], job: dict[str, Any], requirements: list[dict[str, Any]]) -> list[Evidence]:
    evidence: list[Evidence] = []
    skills = profile.get("skills_json")
    if skills:
        # Keep source vocabulary in a short, structured list; do not serialize full profile JSON.
        from app.matching.skill_matcher import resume_skill_names
        names = resume_skill_names(skills)[:30]
        if names:
            evidence.append(Evidence(type="skill", source="resume", text=", ".join(names)[:300]))
    summary = _compact(profile.get("summary"))
    if summary:
        evidence.append(Evidence(type="summary", source="resume", text=summary))
    for row in (profile.get("experience_json") if isinstance(profile.get("experience_json"), list) else [])[:8]:
        if not isinstance(row, dict):
            continue
        text = " — ".join(part for part in (
            _compact(row.get("job_title"), 80), _compact(row.get("company"), 80),
            _compact(row.get("start_date"), 25) + (f"–{_compact(row.get('end_date'), 25)}" if row.get("end_date") else ""),
            _compact(row.get("description"), 180),
        ) if part.strip(" —"))
        if text:
            evidence.append(Evidence(type="experience", source="resume", text=text[:300]))
    for row in (profile.get("education_json") if isinstance(profile.get("education_json"), list) else [])[:6]:
        if not isinstance(row, dict):
            continue
        text = " — ".join(_compact(row.get(key), 120) for key in ("degree", "field_of_study", "institution") if _compact(row.get(key), 120))
        if text:
            evidence.append(Evidence(type="education", source="resume", text=text[:300]))
    for row in (profile.get("projects_json") if isinstance(profile.get("projects_json"), list) else [])[:12]:
        if not isinstance(row, dict):
            continue
        name = _compact(row.get("project_name"), 100)
        details = _compact(row.get("description"), 180)
        technologies = row.get("technologies") if isinstance(row.get("technologies"), list) else []
        tech_text = ", ".join(_compact(item, 60) for item in technologies if isinstance(item, str))[:160]
        text = " — ".join(part for part in (name, details, f"Technologies: {tech_text}" if tech_text else "") if part)
        if text:
            evidence.append(Evidence(type="project", source="resume", text=text[:300]))
    # Job source snippets are useful evidence for expected skills and experience.
    for row in requirements[:30]:
        name = row.get("skill_name")
        if isinstance(name, str) and name.strip():
            level = row.get("skill_type", "required")
            evidence.append(Evidence(type="skill", source="job", text=f"{name.strip()} ({level})"[:300], related_requirement=name.strip()[:160]))
    summary = _compact(job.get("summary") or job.get("cleaned_description") or job.get("description"))
    if summary:
        evidence.append(Evidence(type="summary", source="job", text=summary[:300]))
    responsibilities = job.get("responsibilities")
    if isinstance(responsibilities, list):
        for item in responsibilities[:6]:
            text = _compact(item)
            if text:
                evidence.append(Evidence(type="responsibility", source="job", text=text[:300]))
    education = job.get("education_requirement")
    if isinstance(education, str) and education.strip():
        evidence.append(Evidence(type="education", source="job", text=_compact(education), related_requirement=education.strip()))
    elif isinstance(job.get("education_json"), dict) and job["education_json"]:
        value = job["education_json"]
        labels = [str(item) for key in ("degree_level", "degrees", "fields") for item in (value.get(key) if isinstance(value.get(key), list) else [value.get(key)]) if item]
        if labels:
            evidence.append(Evidence(type="education", source="job", text=_compact(", ".join(labels)), related_requirement=_compact(", ".join(labels))))
    return evidence[:80]
