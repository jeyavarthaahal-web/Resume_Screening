"""Describe Task 6's persisted score components and weights without rescoring."""
from typing import Any

from app.matching.score_calculator import WEIGHTS

_COMPONENTS = (
    ("semantic", "semantic_score", "Semantic Match"),
    ("skills", "skills_score", "Skill Match"),
    ("experience", "experience_score", "Experience Match"),
    ("education", "education_score", "Education Match"),
    ("projects", "projects_score", "Project Match"),
)


def build_score_breakdown(result: dict[str, Any]) -> dict[str, dict[str, float]]:
    breakdown: dict[str, dict[str, float]] = {}
    for component, field, _label in _COMPONENTS:
        weight_key = "skill_score" if component == "skills" else "project_score" if component == "projects" else f"{component}_score"
        weight = WEIGHTS[weight_key]
        score = round(float(result[field]), 2)
        breakdown[component] = {"score": score, "weight": weight, "weighted_contribution": round(score * weight, 2)}
    contribution_total = sum(item["weighted_contribution"] for item in breakdown.values())
    overall = float(result["overall_score"])
    if abs(contribution_total - overall) > 0.03:
        raise ValueError("Persisted score components do not reconcile with the Task 6 overall score.")
    return breakdown


def score_sentences(overall_score: float, breakdown: dict[str, dict[str, float]]) -> list[str]:
    labels = dict((component, label) for component, _field, label in _COMPONENTS)
    lines = [f"The candidate's overall match score is {overall_score:.2f}."]
    for component, values in breakdown.items():
        lines.append(f"{labels[component]} contributed {values['weighted_contribution']:.2f} points ({values['score']:.2f} × {values['weight']:.0%}).")
    return lines
