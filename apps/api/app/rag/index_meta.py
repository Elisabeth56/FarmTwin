"""Ties the search index to the embedder that built it, so query and index vectors always match."""

from sqlalchemy.orm import Session

from app.db import models

EMBEDDER_KEY = "embedder_model"


def stored_embedder(session: Session) -> str | None:
    row = session.get(models.IndexMeta, EMBEDDER_KEY)
    return row.value if row else None


def record_embedder(session: Session, name: str) -> None:
    session.merge(models.IndexMeta(key=EMBEDDER_KEY, value=name))
    session.flush()
