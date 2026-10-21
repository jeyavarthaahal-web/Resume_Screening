"""Transparent fixed default weights for the Task 6 numerical score."""
from typing import Mapping

WEIGHTS: dict[str, float] = {
    "semantic_score": 0.40,
    "skill_score": 0.25,
    "experience_score": 0.15,
    "education_score": 0.10,
    "project_score": 0.10,
}


def calculate_overall_score(scores: Mapping[str, float]) -> float:
    value = sum(float(scores[name]) * weight for name, weight in WEIGHTS.items())
    return round(max(0.0, min(100.0, value)), 2)
