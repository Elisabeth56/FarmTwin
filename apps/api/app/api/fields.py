from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/api/fields", tags=["fields"])


class FieldCreate(BaseModel):
    farm_id: int
    name: str
    area_hectares: float | None = None
    soil_type: str | None = None
    soil_ph_estimate: float | None = None
    notes: str | None = None


class FieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    name: str
    area_hectares: float | None = None
    soil_type: str | None = None
    soil_ph_estimate: float | None = None
    notes: str | None = None


@router.get("", response_model=list[FieldRead])
def list_fields(farm_id: int | None = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Field)
    if farm_id is not None:
        query = query.filter(models.Field.farm_id == farm_id)
    return query.all()


@router.get("/{field_id}", response_model=FieldRead)
def get_field(field_id: int, db: Session = Depends(get_db)):
    field = db.query(models.Field).filter(models.Field.id == field_id).first()
    if not field:
        raise HTTPException(404, "not found")
    return field


@router.post("", response_model=FieldRead)
def create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    field = models.Field(**payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field
