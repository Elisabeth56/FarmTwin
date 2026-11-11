"""Plantings: a crop in a field from a planting date. A field can hold several (intercropping)."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.lookup import farm_or_404, field_or_404, get_or_404
from app.db.session import get_db
from app.errors import AppError

router = APIRouter(prefix="/api/plantings", tags=["plantings"])

CROPS = ("maize", "cassava", "yam", "sorghum", "rice", "cowpea")
STATUSES = ("active", "harvested", "failed")


class PlantingIn(BaseModel):
    field_id: int
    crop_type: str
    variety: str | None = None
    planting_date: date | None = None
    status: str = "active"


class PlantingUpdate(BaseModel):
    variety: str | None = None
    planting_date: date | None = None
    status: str | None = None


class PlantingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    crop_type: str
    variety: str | None
    planting_date: date | None
    status: str | None
    created_at: datetime


def _check(
    crop_type: str | None = None, status: str | None = None, planting_date: date | None = None
) -> None:
    if crop_type is not None and crop_type not in CROPS:
        raise AppError(
            422,
            "invalid_input",
            "FarmTwin doesn't cover that crop yet.",
            {"fields": {"crop_type": f"One of: {', '.join(CROPS)}"}},
        )
    if status is not None and status not in STATUSES:
        raise AppError(
            422,
            "invalid_input",
            "Unknown planting status.",
            {"fields": {"status": f"One of: {', '.join(STATUSES)}"}},
        )
    if planting_date is not None and planting_date > date.today():
        raise AppError(
            422,
            "invalid_input",
            "The planting date is in the future.",
            {"fields": {"planting_date": "Can't be in the future"}},
        )


def _planting_or_404(db: Session, planting_id: int) -> models.Planting:
    return get_or_404(
        db, models.Planting, planting_id, "planting_not_found", "That planting no longer exists."
    )


@router.get("", response_model=list[PlantingOut])
def list_plantings(
    farm_id: int | None = Query(None), field_id: int | None = Query(None), db: Session = Depends(get_db)
):
    if farm_id is None and field_id is None:
        raise AppError(
            422,
            "invalid_input",
            "Say which farm or field.",
            {"fields": {"farm_id": "Required without field_id"}},
        )
    query = select(models.Planting).order_by(models.Planting.id)
    if field_id is not None:
        field_or_404(db, field_id)
        query = query.where(models.Planting.field_id == field_id)
    if farm_id is not None:
        farm_or_404(db, farm_id)
        query = query.join(models.Field).where(models.Field.farm_id == farm_id)
    return db.scalars(query).all()


@router.post("", response_model=PlantingOut, status_code=201)
def create_planting(body: PlantingIn, db: Session = Depends(get_db)):
    body.crop_type = body.crop_type.strip().lower()
    _check(body.crop_type, body.status, body.planting_date)
    field_or_404(db, body.field_id)
    planting = models.Planting(**body.model_dump())
    db.add(planting)
    db.commit()
    db.refresh(planting)
    return planting


@router.get("/{planting_id}", response_model=PlantingOut)
def get_planting(planting_id: int, db: Session = Depends(get_db)):
    return _planting_or_404(db, planting_id)


@router.patch("/{planting_id}", response_model=PlantingOut)
def update_planting(planting_id: int, body: PlantingUpdate, db: Session = Depends(get_db)):
    planting = _planting_or_404(db, planting_id)
    changes = body.model_dump(exclude_unset=True)
    _check(status=changes.get("status"), planting_date=changes.get("planting_date"))
    for key, value in changes.items():
        setattr(planting, key, value)
    db.commit()
    db.refresh(planting)
    return planting


@router.delete("/{planting_id}", status_code=204)
def delete_planting(planting_id: int, db: Session = Depends(get_db)):
    db.delete(_planting_or_404(db, planting_id))
    db.commit()
    return Response(status_code=204)
