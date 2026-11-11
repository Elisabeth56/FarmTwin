"""Fetch-or-404 for routers, so every missing record reports the same way."""

from typing import TypeVar

from sqlalchemy.orm import Session

from app.db.session import Base
from app.errors import AppError

M = TypeVar("M", bound=Base)


def get_or_404(db: Session, model: type[M], record_id: int, code: str, message: str) -> M:
    record = db.get(model, record_id)
    if record is None:
        raise AppError(404, code, message)
    return record


def farm_or_404(db: Session, farm_id: int):
    from app.db.models import Farm

    return get_or_404(db, Farm, farm_id, "farm_not_found", "That farm no longer exists.")


def field_or_404(db: Session, field_id: int):
    from app.db.models import Field

    return get_or_404(db, Field, field_id, "field_not_found", "That field no longer exists.")
