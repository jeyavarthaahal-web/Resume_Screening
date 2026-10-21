"""Build factual, deterministic explanations from Task 6 scores and structured sources."""
from datetime import datetime, timezone
from typing import Any

from app.ranking.evidence_extractor import extract_evidence
from app.ranking.score_explainer import build_score_breakdown, score_sentences
from app.ranking.skill_explainer import classify_skills
from app.schemas.ranking import (
    EducationContext, Evidence, ExperienceContext, Gap, RankingExplanation,
    RelevantProject, SkillClassification, Strength,
)
from app.matching.skill_matcher import normalize_skill, resume_skill_names


def _text(value: Any, limit: int = 240) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _education_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return list(dict.fromkeys(text for item in value for text in _education_values(item)))
    if isinstance(value, dict):
        return list(dict.fromkeys(text for key in ("degree", "field_of_study", "degree_level", "degrees", "fields") for text in _education_values(value.get(key))))
    return []


def _education_context(profile: dict[str, Any], job: dict[str, Any], score: float) -> EducationContext:
    candidate = _education_values(profile.get("education_json"))
    requirement = _education_values(job.get("education_json"))
    fallback = _text(job.get("education_requirement"))
    if fallback:
        requirement.append(fallback)
    requirement = list(dict.fromkeys(requirement))
    if not requirement:
        status = "not_specified"
    elif not candidate:
        status = "not_identified"
    else:
        status = "matched" if score >= 80 else "partial"
    return EducationContext(candidate=candidate[:8], requirement=requirement[:8], status=status)


def _experience_context(profile: dict[str, Any], job: dict[str, Any]) -> ExperienceContext:
    candidate = profile.get("years_experience")
    minimum = job.get("experience_min")
    maximum = job.get("experience_max")
    if candidate is None and (minimum is not None or maximum is not None):
        status = "not_identified"
    elif minimum is None and maximum is not None:
        status = "maximum_only"
    elif minimum is None and maximum is None:
        status = "not_specified"
    else:
        status = "below_requirement" if minimum is not None and float(candidate) < float(minimum) else "matched"
    return ExperienceContext(
        candidate_years=float(candidate) if candidate is not None else None,
        minimum_years=float(minimum) if minimum is not None else None,
        maximum_years=float(maximum) if maximum is not None else None,
        status=status,
    )


def _skill_evidence(skill: str, evidence: list[Evidence], source: str) -> list[Evidence]:
    needle = normalize_skill(skill)
    selected = [item for item in evidence if item.source == source and item.type == "skill" and (
        normalize_skill(item.related_requirement or item.text.split(" (", 1)[0]) == needle
        if source == "job" else any(normalize_skill(part) == needle for part in item.text.split(", "))
    )]
    return selected[:2]


def _project_evidence(profile: dict[str, Any], required_names: list[str]) -> list[RelevantProject]:
    projects = profile.get("projects_json") if isinstance(profile.get("projects_json"), list) else []
    output: list[RelevantProject] = []
    for project in projects[:20]:
        if not isinstance(project, dict):
            continue
        name = _text(project.get("project_name"), 100)
        technologies = project.get("technologies") if isinstance(project.get("technologies"), list) else []
        technologies = list(dict.fromkeys(_text(value, 60) for value in technologies if isinstance(value, str) and _text(value, 60)))
        related = [requirement for requirement in required_names if any(normalize_skill(technology) == normalize_skill(requirement) for technology in technologies)]
        if not related or not name:
            continue
        description = _text(project.get("description"), 160)
        snippet = " — ".join(part for part in (name, description, f"Technologies: {', '.join(technologies)}" if technologies else "") if part)
        output.append(RelevantProject(
            project_name=name, relevant_technologies=technologies,
            related_job_requirements=related[:12],
            evidence=Evidence(type="project", source="resume", text=snippet[:300]),
        ))
    return output[:12]


def build_explanation(
    result: dict[str, Any], profile: dict[str, Any], job: dict[str, Any], requirements: list[dict[str, Any]],
) -> RankingExplanation:
    """Explain persisted numbers and source fields; this function never scores a candidate."""
    score_breakdown = build_score_breakdown(result)
    overall = round(float(result["overall_score"]), 2)
    classified = classify_skills(profile.get("skills_json"), requirements)
    evidence = extract_evidence(profile, job, requirements)
    matched = [SkillClassification.model_validate(item) for item in classified["matched"]]
    partial = [SkillClassification.model_validate(item) for item in classified["partial"]]
    missing = [SkillClassification.model_validate(item) for item in classified["missing"]]
    exp = _experience_context(profile, job)
    edu = _education_context(profile, job, float(result["education_score"]))
    req_names = list(dict.fromkeys(row.name for row in matched + partial + missing))
    relevant_projects = _project_evidence(profile, req_names)

    strengths: list[Strength] = []
    matched_required = [item for item in matched if item.importance == "required"]
    if matched_required:
        support = [item for skill in matched_required for item in _skill_evidence(skill.name, evidence, "resume")]
        support += [item for skill in matched_required for item in _skill_evidence(skill.name, evidence, "job")]
        strengths.append(Strength(
            title="Required skill alignment",
            description="The extracted resume skills include these required job skills: " + ", ".join(item.name for item in matched_required[:12]) + ".",
            evidence=support[:12],
        ))
    if exp.status == "matched" and exp.minimum_years is not None:
        support = [item for item in evidence if item.type == "experience" and item.source == "resume"][:3]
        if exp.candidate_years is not None:
            support.append(Evidence(type="experience", source="resume", text=f"Task 4 extracted experience: {exp.candidate_years:g} years"))
        support.append(Evidence(type="experience", source="job", text=f"Stated minimum: {exp.minimum_years:g} years"))
        strengths.append(Strength(title="Experience meets the stated minimum", description=f"Task 4 extracted {exp.candidate_years:g} years; the role states a minimum of {exp.minimum_years:g} years.", evidence=support))
    if edu.status == "matched" and edu.candidate:
        support = [item for item in evidence if item.type == "education" and item.source in {"resume", "job"}]
        strengths.append(Strength(title="Education requirement alignment", description="The extracted education information is compatible with the stated requirement under the Task 6 education matcher.", evidence=support[:6]))
    if relevant_projects and float(result["projects_score"]) >= 50:
        strengths.append(Strength(
            title="Project evidence related to job skills",
            description="These extracted projects list technologies that match job skill requirements.",
            evidence=[project.evidence for project in relevant_projects[:6]],
        ))
    if float(result["semantic_score"]) >= 70:
        resume_summary = next((item for item in evidence if item.source == "resume" and item.type == "summary"), None)
        job_summary = next((item for item in evidence if item.source == "job" and item.type == "summary"), None)
        support = [item for item in (resume_summary, job_summary) if item]
        if resume_summary and job_summary:
            strengths.append(Strength(title="Strong semantic alignment", description=f"The stored semantic similarity score is {float(result['semantic_score']):.2f} out of 100.", evidence=support))

    gaps: list[Gap] = []
    for skill in missing:
        job_evidence = _skill_evidence(skill.name, evidence, "job")
        resume_skills = resume_skill_names(profile.get("skills_json"))
        resume_ref = [Evidence(type="skill", source="resume", text="Extracted skills: " + ", ".join(resume_skills[:30]))] if resume_skills else []
        gaps.append(Gap(
            title=f"{skill.name} not identified in extracted skills",
            description=f"{skill.name} is a {skill.importance} job skill and was not identified in the structured resume skills.",
            severity=skill.importance, status="missing", evidence=(job_evidence + resume_ref)[:3],
        ))
    for skill in partial:
        source = Evidence(type="skill", source="resume", text=f"{skill.resume_skill} is listed in extracted resume skills.")
        gaps.append(Gap(
            title=f"Partial match for {skill.name}",
            description=f"The resume lists related skill {skill.resume_skill}; it is not an exact {skill.name} match.",
            severity=skill.importance, status="partial", evidence=[source, *_skill_evidence(skill.name, evidence, "job")],
        ))
    if exp.status == "below_requirement" and exp.candidate_years is not None and exp.minimum_years is not None:
        gaps.append(Gap(
            title="Extracted experience below stated minimum",
            description=f"Task 4 extracted {exp.candidate_years:g} years; the job states a minimum of {exp.minimum_years:g} years.",
            severity="required", status="below_requirement",
            evidence=[Evidence(type="experience", source="resume", text=f"Task 4 extracted experience: {exp.candidate_years:g} years"), Evidence(type="experience", source="job", text=f"Stated minimum: {exp.minimum_years:g} years")],
        ))
    elif exp.status == "not_identified":
        gaps.append(Gap(title="Experience information not identified", description="Experience information was not clearly identified in the extracted resume profile, so it cannot be compared with the stated requirement.", severity="informational", status="not_identified"))
    if edu.status == "not_identified":
        gaps.append(Gap(title="Education information not identified", description="No structured candidate education was identified for comparison with the job requirement.", severity="informational", status="not_identified"))
    if edu.status == "partial":
        gaps.append(Gap(title="Education requirement partially matched", description="The Task 6 education matcher found incomplete compatibility with the stated education requirement.", severity="informational", status="partial", evidence=[item for item in evidence if item.type == "education"][:4]))
    project_rows = profile.get("projects_json") if isinstance(profile.get("projects_json"), list) else []
    has_project_data = any(isinstance(row, dict) and any(row.get(key) for key in ("project_name", "description", "technologies", "role")) for row in project_rows)
    if has_project_data and float(result["projects_score"]) < 50:
        gaps.append(Gap(title="Limited identified project relevance", description="The stored Task 6 project relevance score is below 50; this describes extracted project evidence only.", severity="informational", status="partial", evidence=[item for item in evidence if item.type == "project"][:4]))

    experience_rows = profile.get("experience_json") if isinstance(profile.get("experience_json"), list) else []
    education = _education_values(profile.get("education_json"))
    populated = sum((
        bool(_text(profile.get("summary"))), bool(resume_skill_names(profile.get("skills_json"))),
        any(isinstance(row, dict) and any(row.get(key) for key in ("job_title", "company", "description", "start_date", "end_date")) for row in experience_rows),
        bool(education), has_project_data,
    ))
    quality = "complete" if populated >= 4 else "partially_complete" if populated >= 2 else "limited"
    quality_note = f"{populated} of 5 structured resume sections (summary, skills, experience, education, projects) contain extracted data. This indicates extraction completeness, not candidate quality."

    lines = score_sentences(overall, score_breakdown)
    if matched:
        lines.append("Extracted resume skills matching job requirements: " + ", ".join(item.name for item in matched[:20]) + ".")
    if partial:
        lines.append("Related but non-exact skills identified: " + ", ".join(f"{item.resume_skill} for {item.name}" for item in partial[:12]) + ".")
    if missing:
        lines.append("Job skills not identified in the extracted resume skills: " + ", ".join(item.name for item in missing[:20]) + ".")
    if exp.status == "matched" and exp.candidate_years is not None and exp.minimum_years is not None:
        lines.append(f"Task 4 extracted {exp.candidate_years:g} years of experience compared with a stated minimum of {exp.minimum_years:g} years.")
    elif exp.status == "below_requirement" and exp.candidate_years is not None and exp.minimum_years is not None:
        lines.append(f"Task 4 extracted {exp.candidate_years:g} years of experience compared with a stated minimum of {exp.minimum_years:g} years.")
    elif exp.status == "not_identified":
        lines.append("Experience information was not clearly identified in the resume.")
    elif exp.status == "maximum_only" and exp.candidate_years is not None:
        lines.append(f"Task 4 extracted {exp.candidate_years:g} years; the job lists a maximum of {exp.maximum_years:g} years and no minimum.")
    if edu.status == "matched" and edu.candidate and edu.requirement:
        lines.append(f"Education comparison: candidate {', '.join(edu.candidate[:3])}; job requirement {', '.join(edu.requirement[:3])}.")
    elif edu.status == "not_identified":
        lines.append("Education information was not identified in the resume.")
    if relevant_projects:
        lines.append("Projects with explicitly listed technologies related to job skills: " + ", ".join(project.project_name for project in relevant_projects[:10]) + ".")

    return RankingExplanation(
        job_id=result["job_id"], resume_id=result["resume_id"], candidate_id=result["candidate_id"],
        overall_score=overall, score_breakdown=score_breakdown,
        matched_skills=matched, partial_skills=partial, missing_skills=missing,
        strengths=strengths, gaps=gaps, evidence=evidence, explanation="\n".join(lines),
        experience_context=exp, education_context=edu, relevant_projects=relevant_projects,
        data_quality=quality, data_quality_note=quality_note, generated_at=datetime.now(timezone.utc),
    )
