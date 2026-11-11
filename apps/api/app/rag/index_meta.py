"""Ties the search index to the embedder that built it, so query and index vectors always match."""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import models

EMBEDDER_KEY = "embedder_model"


class IndexMismatchError(RuntimeError):
    pass


def stored_embedder(session: Session) -> str | None:
    row = session.get(models.IndexMeta, EMBEDDER_KEY)
    return row.value if row else None


def record_embedder(session: Session, name: str) -> None:
    session.merge(models.IndexMeta(key=EMBEDDER_KEY, value=name))
    session.flush()


def check_index_embedder(session: Session) -> None:
    """Fails startup when the index was built with a different embedder than the one configured."""
    if session.query(models.DocumentChunk.id).first() is None:
        return
    built_with = stored_embedder(session) or "an older version of FarmTwin"
    configured = get_settings().embedder_model
    if built_with != configured:
        raise IndexMismatchError(
            f"FarmTwin's search index was built with {built_with}, but this version uses "
            f"{configured}. Rebuild it with `uv run python scripts/ingest.py`."
        )
