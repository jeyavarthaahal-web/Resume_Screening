"""Degree-level and field-aware education compatibility scoring."""
import re
from typing import Any

_LEVELS = {
    "high_school": 0, "secondary": 0, "diploma": 1, "associate": 1,
    "bachelor": 2, "b.tech": 2, "btech": 2, "b.e.": 2, "b.sc": 2,
    "master": 3, "m.tech": 3, "mtech": 3, "mba": 3, "m.sc": 3,
    "phd": 4, "ph.d": 4, "doctorate": 4,
}
_FIELD_GROUPS = (
    {"computer science", "computer engineering", "software engineering", "information technology", "information systems"},
    {"artificial intelligence", "ai", "machine learning", "data science", "analytics"},
    {"electrical engineering", "electronics", "computer engineering"},
)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str): return [value]
    if isinstance(value, list): return [item for entry in value for item in _strings(entry)]
    if isinstance(value, dict):
        return [str(v) for k, v in value.items() if k in {"degree", "field_of_study", "degree_level", "degrees", "fields"} for v in _strings(v)]
    return []


def _level(text: str) -> int | None:
    value = text.casefold()
    for term, level in sorted(_LEVELS.items(), key=lambda item: len(item[0]), reverse=True):
        if term in value: return level
    return None


def _field_matches(candidate: str, required: str) -> bool:
    c, r = candidate.casefold(), required.casefold()
    if c == r or c in r or r in c: return True
    return any(c in group and r in group for group in _FIELD_GROUPS)


def education_score(candidate_education: Any, job_education: Any, fallback_requirement: str | None = None) -> float:
    required = _strings(job_education) if job_education is not None else []
    if fallback_requirement: required.append(fallback_requirement)
    if not required: return 100.0
    candidate = _strings(candidate_education)
    if not candidate: return 50.0
    required_text, candidate_text = " ".join(required), " ".join(candidate)
    req_level, cand_level = _level(required_text), _level(candidate_text)
    req_fields = [field for group in _FIELD_GROUPS for field in group if re.search(rf"(?<!\w){re.escape(field)}(?!\w)", required_text, re.I)]
    cand_fields = [field for group in _FIELD_GROUPS for field in group if re.search(rf"(?<!\w){re.escape(field)}(?!\w)", candidate_text, re.I)]
    if req_level is None and not req_fields: return 50.0
    if req_level is None: level_component = 100.0
    elif cand_level is None: level_component = 50.0
    elif cand_level >= req_level: level_component = 100.0
    else: level_component = max(0.0, cand_level / max(1, req_level) * 100)
    if not req_fields: return round(level_component, 2)
    if not cand_fields: field_component = 50.0
    else: field_component = 100.0 if any(_field_matches(c, r) for c in cand_fields for r in req_fields) else 0.0
    if req_level is None: return round(field_component, 2)
    return round(level_component * 0.60 + field_component * 0.40, 2)
