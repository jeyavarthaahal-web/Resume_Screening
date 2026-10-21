"""Lazy, process-wide CPU Sentence Transformer loader."""
from threading import RLock
from typing import Any

from app.config import get_settings


class ModelUnavailableError(RuntimeError):
    """The configured embedding model could not be loaded."""


class ModelManager:
    def __init__(self) -> None:
        self._model: Any | None = None
        self._model_name: str | None = None
        self._lock = RLock()

    def get_model(self) -> Any:
        settings = get_settings()
        model_name = settings.embedding_model.strip() or "sentence-transformers/all-MiniLM-L6-v2"
        with self._lock:
            if self._model is not None and self._model_name == model_name:
                return self._model
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(model_name, device="cpu")
                model.eval()
            except Exception as exc:
                raise ModelUnavailableError(
                    "The matching model is unavailable. Install backend requirements and allow the first-run model download, then retry."
                ) from exc
            self._model = model
            self._model_name = model_name
            return model

    @property
    def model_name(self) -> str:
        return self._model_name or get_settings().embedding_model


model_manager = ModelManager()
