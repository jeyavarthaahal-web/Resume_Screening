"""Canonicalized skill overlap reusing Tasks 4 and 5 skill vocabularies."""
import re
from dataclasses import dataclass
from typing import Any, Iterable

from app.nlp.job_extractor import SKILLS as JOB_SKILLS
from app.nlp.resume_extractor import SKILL_ALIASES as RESUME_SKILLS


def _key(value: str) -> str:
    text = value.strip().casefold()
    if text in {".net", "net"}: return "dotnet"
    if text in {"c++", "c#"}: return text
    return re.sub(r"[^a-z0-9]+", "", text)


_ALIAS_TO_CANONICAL: dict[str, str] = {}
SKILL_CATEGORIES: dict[str, str] = {}
for category, skills in RESUME_SKILLS.items():
    category_name = {"cloud": "cloud_platform", "databases": "database", "programming_languages": "programming_language"}.get(category, category.rstrip("s"))
    for canonical, aliases in skills.items():
        SKILL_CATEGORIES[canonical] = category_name
        for name in (canonical, *aliases): _ALIAS_TO_CANONICAL.setdefault(_key(name), canonical)
for canonical, (category, _bucket, aliases) in JOB_SKILLS.items():
    SKILL_CATEGORIES.setdefault(canonical, category)
    for name in (canonical, *aliases): _ALIAS_TO_CANONICAL.setdefault(_key(name), canonical)
for canonical, aliases in {
    "TypeScript": ("ts",), "PostgreSQL": ("postgres",), "Kubernetes": ("k8s",),
    "Scikit-learn": ("sklearn", "scikit learn"), "TensorFlow": ("tf",),
    "Natural Language Processing": ("nlp",), "Machine Learning": ("ml",),
    "React": ("reactjs", "react.js"), "Node.js": ("nodejs",), "JavaScript": ("js",),
}.items():
    for name in (canonical, *aliases): _ALIAS_TO_CANONICAL.setdefault(_key(name), canonical)


def normalize_skill(skill: str) -> str:
    value = skill.strip()
    return _ALIAS_TO_CANONICAL.get(_key(value), re.sub(r"\s+", " ", value).casefold())


def canonical_skill_category(skill: str) -> str | None:
    return SKILL_CATEGORIES.get(normalize_skill(skill))


def _strings(value: Any) -> list[str]:
    if isinstance(value, str): return [value]
    if isinstance(value, list): return [item for entry in value for item in _strings(entry)]
    if isinstance(value, dict):
        if isinstance(value.get("name"), str): return [value["name"]]
        return [item for entry in value.values() for item in _strings(entry)]
    return []


def resume_skill_names(skills_json: Any) -> list[str]:
    return list(dict.fromkeys(_strings(skills_json)))


def job_skill_names(requirements: Iterable[Any], importance: str | None = None) -> list[str]:
    values: list[str] = []
    for item in requirements:
        if isinstance(item, dict):
            level = item.get("skill_type", item.get("importance", "required"))
            name = item.get("name", item.get("skill_name"))
            allowed = {"preferred", "nice_to_have"} if importance == "preferred" else {"required"}
            if name and (importance is None or level in allowed): values.append(str(name))
        elif isinstance(item, str): values.append(item)
    return list(dict.fromkeys(values))


@dataclass(frozen=True)
class SkillScore:
    score: float
    required_ratio: float | None
    preferred_ratio: float | None
    matched_required: int
    matched_preferred: int


def _ratio(resume: set[str], job_skills: list[str]) -> tuple[float | None, int]:
    if not job_skills: return None, 0
    matched = sum(1 for skill in job_skills if normalize_skill(skill) in resume)
    return matched / len(job_skills), matched


def calculate_skill_score(resume_skills: Any, required: Iterable[Any], preferred: Iterable[Any]) -> SkillScore:
    resume = {normalize_skill(skill) for skill in resume_skill_names(resume_skills)}
    required_names = job_skill_names(required)
    preferred_names = job_skill_names(preferred)
    required_ratio, req_count = _ratio(resume, required_names)
    preferred_ratio, pref_count = _ratio(resume, preferred_names)
    if required_ratio is None and preferred_ratio is None: score = 50.0
    elif required_ratio is None: score = preferred_ratio * 100  # type: ignore[operator]
    elif preferred_ratio is None: score = required_ratio * 100
    else: score = (required_ratio * 0.70 + preferred_ratio * 0.30) * 100
    return SkillScore(round(score, 2), required_ratio, preferred_ratio, req_count, pref_count)
