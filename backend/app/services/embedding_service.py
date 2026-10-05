"""Open-source sentence embeddings for CV ↔ job similarity (all-MiniLM-L6-v2)."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_MODEL = None
_MODEL_ERROR: Optional[str] = None
_BACKEND: Literal["sentence_transformers", "sklearn_tfidf", "none"] = "none"


def _load_sklearn_backend() -> bool:
    global _MODEL, _MODEL_ERROR, _BACKEND
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        _MODEL = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        _BACKEND = "sklearn_tfidf"
        _MODEL_ERROR = None
        return True
    except Exception as exc:
        _BACKEND = "none"
        _MODEL_ERROR = str(exc)
        logger.error("Failed to load sklearn TF-IDF backend: %s", exc)
        return False


def _load_sentence_transformer() -> bool:
    global _MODEL, _MODEL_ERROR, _BACKEND
    try:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        model_name = settings.embedding_model
        try:
            _MODEL = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            _MODEL = SentenceTransformer(model_name)
        _BACKEND = "sentence_transformers"
        _MODEL_ERROR = None
        return True
    except Exception as exc:
        _MODEL = None
        _MODEL_ERROR = str(exc)
        logger.error("Failed to load sentence-transformers model: %s", exc)
        return False


def _load_model() -> None:
    global _BACKEND
    if _BACKEND != "none":
        return

    settings = get_settings()
    if settings.embedding_backend == "sklearn_tfidf":
        _load_sklearn_backend()
        return

    if settings.embedding_backend == "sentence_transformers":
        if not _load_sentence_transformer():
            _load_sklearn_backend()
        return

    if _load_sentence_transformer():
        return
    _load_sklearn_backend()


def embeddings_available() -> bool:
    _load_model()
    return _BACKEND != "none"


def embedding_model_name() -> str:
    settings = get_settings()
    if _BACKEND == "sklearn_tfidf":
        return "sklearn-tfidf-cosine (embedding fallback)"
    return settings.embedding_model


def embedding_similarity_percent(text_a: str, text_b: str) -> int:
    from sklearn.metrics.pairwise import cosine_similarity

    _load_model()
    if _MODEL is None:
        raise RuntimeError(_MODEL_ERROR or "Embedding model is not available.")

    if _BACKEND == "sentence_transformers":
        vec_a = _MODEL.encode(text_a or "", normalize_embeddings=True)
        vec_b = _MODEL.encode(text_b or "", normalize_embeddings=True)
        score = float(cosine_similarity([vec_a], [vec_b])[0][0])
        return max(0, min(100, round(score * 100)))

    matrix = _MODEL.fit_transform([text_a or "", text_b or ""])
    score = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    return max(0, min(100, round(score * 100)))


@lru_cache(maxsize=1)
def get_embedding_status() -> dict:
    _load_model()
    settings = get_settings()
    if _BACKEND == "none":
        return {
            "available": False,
            "model": settings.embedding_model,
            "backend": "none",
            "error": _MODEL_ERROR,
        }
    return {
        "available": True,
        "model": embedding_model_name(),
        "backend": _BACKEND,
        "error": _MODEL_ERROR,
    }
