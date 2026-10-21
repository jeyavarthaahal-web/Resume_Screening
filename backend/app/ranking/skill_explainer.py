"""Conservative skill classifications using Task 6 normalization and curated relations."""
from typing import Any, Literal

from app.matching.skill_matcher import job_skill_names, normalize_skill, resume_skill_names

SkillImportance = Literal["required", "preferred"]

# These pairs are related but not interchangeable; aliases handled by normalize_skill are matches.
_RELATED = {
    frozenset(("aws", "azure")), frozenset(("aws", "google cloud")),
    frozenset(("react", "angular")), frozenset(("react", "vue")),
    frozenset(("angular", "vue")), frozenset(("postgresql", "mysql")),
    frozenset(("postgresql", "sqlite")), frozenset(("mysql", "sqlite")),
    frozenset(("javascript", "typescript")), frozenset(("node.js", "javascript")),
}


def _importance(row: Any) -> SkillImportance:
    if isinstance(row, dict):
        value = row.get("skill_type", row.get("importance", "required"))
        return "preferred" if value in {"preferred", "nice_to_have"} else "required"
    return "required"


def _job_rows(requirements: list[dict[str, Any]]) -> list[tuple[str, SkillImportance]]:
    output: dict[str, tuple[str, SkillImportance]] = {}
    for row in requirements:
        name = row.get("skill_name") or row.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        key = normalize_skill(name)
        importance = _importance(row)
        existing = output.get(key)
        if existing is None or (existing[1] == "preferred" and importance == "required"):
            output[key] = (name, importance)
    # Keep deterministic source ordering rather than ranking requirements.
    return list(output.values())


def classify_skills(resume_skills: Any, requirements: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    source_skills = resume_skill_names(resume_skills)
    normalized_to_source: dict[str, str] = {}
    for skill in source_skills:
        normalized_to_source.setdefault(normalize_skill(skill), skill)
    source_keys = set(normalized_to_source)
    output: dict[str, list[dict[str, str]]] = {"matched": [], "partial": [], "missing": []}
    for required_name, importance in _job_rows(requirements):
        key = normalize_skill(required_name)
        if key in source_keys:
            output["matched"].append({"name": required_name, "importance": importance, "status": "matched", "resume_skill": normalized_to_source[key]})
            continue
        related = next((normalized_to_source[candidate] for candidate in normalized_to_source if frozenset((key.casefold(), candidate.casefold())) in _RELATED), None)
        if related:
            output["partial"].append({"name": required_name, "importance": importance, "status": "partial", "resume_skill": related})
        else:
            output["missing"].append({"name": required_name, "importance": importance, "status": "missing"})
    return output


def job_skill_groups(requirements: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    return job_skill_names(requirements, "required"), job_skill_names(requirements, "preferred")
