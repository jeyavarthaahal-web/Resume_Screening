"""Bounded embedding cache and CPU inference wrapper."""
from collections import OrderedDict
from threading import RLock
from typing import Sequence

from app.ai.model_manager import ModelManager, model_manager


class EmbeddingError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(self, manager: ModelManager = model_manager, max_cache_entries: int = 512) -> None:
        self.manager = manager
        self.max_cache_entries = max(1, max_cache_entries)
        self._cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self._cache_lock = RLock()
        self._inference_lock = RLock()

    def encode_text(self, text: str) -> list[float]:
        return self.encode_texts([text])[0] if text and text.strip() else []

    def encode_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        normalized = [text.strip() if isinstance(text, str) else "" for text in texts]
        results: list[tuple[float, ...] | None] = [None] * len(normalized)
        missing_by_text: OrderedDict[str, list[int]] = OrderedDict()
        with self._cache_lock:
            for index, text in enumerate(normalized):
                if not text:
                    results[index] = ()
                elif text in self._cache:
                    self._cache.move_to_end(text)
                    results[index] = self._cache[text]
                else:
                    missing_by_text.setdefault(text, []).append(index)
        if missing_by_text:
            try:
                with self._inference_lock:
                    # A competing request may have populated the cache while we waited.
                    pending = [text for text in missing_by_text if text not in self._cache]
                    vectors: list[tuple[float, ...]] = []
                    if pending:
                        model = self.manager.get_model()
                        encoded = model.encode(
                            pending,
                            batch_size=32,
                            show_progress_bar=False,
                            convert_to_numpy=True,
                            normalize_embeddings=True,
                        )
                        vectors = [tuple(float(value) for value in row) for row in encoded]
                    vector_by_text = dict(zip(pending, vectors, strict=True))
                    with self._cache_lock:
                        for text in missing_by_text:
                            vector = self._cache.get(text) or vector_by_text.get(text)
                            if vector is None:
                                raise EmbeddingError("The matching model returned an incomplete embedding batch.")
                            self._cache[text] = vector
                            self._cache.move_to_end(text)
                            while len(self._cache) > self.max_cache_entries:
                                self._cache.popitem(last=False)
                            for index in missing_by_text[text]:
                                results[index] = vector
            except EmbeddingError:
                raise
            except Exception as exc:
                raise EmbeddingError("Text embeddings could not be generated. Please retry the match.") from exc
        return [list(vector or ()) for vector in results]

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()


embedding_service = EmbeddingService()
