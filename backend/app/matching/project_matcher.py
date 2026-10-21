"""Project-to-role fit from explicit technology overlap and semantic context."""
from typing import Any, Sequence

from app.ai.embedding_service import EmbeddingService, embedding_service
from app.ai.semantic_matcher import semantic_score_from_vectors
from app.matching.skill_matcher import calculate_skill_score, resume_skill_names


def project_score(
    projects: Sequence[dict[str, Any]],
    required_skills: list[str],
    preferred_skills: list[str],
    job_project_context: str,
    embeddings: dict[str, list[float]],
    service: EmbeddingService = embedding_service,
) -> float:
    if not projects:
        return 50.0  # No project evidence is neutral, not perfect qualification.
    if not required_skills and not preferred_skills and not job_project_context.strip():
        return 50.0
    job_targets = required_skills + preferred_skills
    per_project: list[float] = []
    for project in projects:
        technologies = resume_skill_names(project.get("technologies", []))
        technology_score = calculate_skill_score(technologies, required_skills, preferred_skills).score if job_targets else None
        description = " ".join(str(project.get(key) or "") for key in ("project_name", "role", "description", "technologies")).strip()
        semantic = None
        if description and job_project_context:
            left, right = service.encode_texts([description, job_project_context])
            semantic = semantic_score_from_vectors(left, right)
        components = []
        if technology_score is not None: components.append((technology_score, 0.60))
        if semantic is not None: components.append((semantic, 0.40))
        if components:
            total_weight = sum(weight for _, weight in components)
            per_project.append(sum(score * weight for score, weight in components) / total_weight)
    return round(max(per_project), 2) if per_project else 50.0
