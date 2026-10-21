"""Semantic comparison helpers using normalized sentence embeddings."""
from app.ai.embedding_service import EmbeddingService, embedding_service


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)))


def semantic_score_from_vectors(left: list[float], right: list[float]) -> float:
    """Map cosine [-1, 1] to a non-negative evidence score: max(0, cosine) * 100."""
    return round(max(0.0, cosine_similarity(left, right)) * 100, 2)


def semantic_similarity(left_text: str, right_text: str, service: EmbeddingService = embedding_service) -> float:
    if not left_text.strip() or not right_text.strip():
        return 0.0
    left, right = service.encode_texts([left_text, right_text])
    return semantic_score_from_vectors(left, right)
