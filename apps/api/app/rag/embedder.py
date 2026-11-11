"""Text embeddings with fastembed (ADR-016). The model is read from a local folder, never fetched
at runtime; `scripts/fetch_embedder.py` puts it there at build or setup time."""

import logging
from collections.abc import Iterable
from typing import Any

from app.config import get_settings
from app.errors import AppError

logger = logging.getLogger(__name__)

EMBEDDER_MISSING = "embedder_missing"

_model: Any = None


def get_model(local_files_only: bool = True):
    """Loads the embedder once. Raises AppError if its files aren't on disk."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        settings = get_settings()
        try:
            _model = TextEmbedding(
                settings.embedder_model,
                cache_dir=str(settings.embedder_path),
                local_files_only=local_files_only,
            )
        except ValueError as exc:
            raise AppError(
                503,
                EMBEDDER_MISSING,
                "FarmTwin's search model is missing. Reinstall the app to restore it.",
                {"path": str(settings.embedder_path)},
            ) from exc
        logger.info("embedder loaded model=%s", settings.embedder_model)
    return _model


def embed_query(text: str) -> list[float]:
    return next(iter(get_model().query_embed(text))).tolist()


def embed_passages(texts: Iterable[str]) -> list[list[float]]:
    return [vec.tolist() for vec in get_model().passage_embed(list(texts))]
