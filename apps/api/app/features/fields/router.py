"""Fields belong to a farm; plantings and observations hang off them."""

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.lookup import farm_or_404, field_or_404
from app.db.session import get_db

router = APIRouter(prefix="/api/fields", tags=["fields"])


class FieldIn(BaseModel):
    farm_id: int
    name: str = Field(min_length=1, max_length=120)
    area_hectares: float | None = Field(default=None, gt=0)
    soil_type: str | None = None
    soil_ph_estimate: float | None = Field(default=None, ge=0, le=14)
    notes: str | None = None


class FieldUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    area_hectares: float | None = Field(default=None, gt=0)
    soil_type: str | None = None
    soil_ph_estimate: float | None = Field(default=None, ge=0, le=14)
    notes: str | None = None


class FieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    name: str
    area_hectares: float | None
    soil_type: str | None
    soil_ph_estimate: float | None
    notes: str | None


@router.get("", response_model=list[FieldOut])
def list_fields(farm_id: int = Query(...), db: Session = Depends(get_db)):
    farm_or_404(db, farm_id)
    return db.scalars(
        select(models.Field).where(models.Field.farm_id == farm_id).order_by(models.Field.id)
    ).all()


@router.post("", response_model=FieldOut, status_code=201)
def create_field(body: FieldIn, db: Session = Depends(get_db)):
    farm_or_404(db, body.farm_id)
    field = models.Field(**body.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/{field_id}", response_model=FieldOut)
def get_field(field_id: int, db: Session = Depends(get_db)):
    return field_or_404(db, field_id)


@router.patch("/{field_id}", response_model=FieldOut)
def update_field(field_id: int, body: FieldUpdate, db: Session = Depends(get_db)):
    field = field_or_404(db, field_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}", status_code=204)
def delete_field(field_id: int, db: Session = Depends(get_db)):
    db.delete(field_or_404(db, field_id))
    db.commit()
    return Response(status_code=204)
