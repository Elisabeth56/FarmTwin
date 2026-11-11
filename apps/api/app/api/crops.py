from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.errors import AppError

router = APIRouter(prefix="/api/crops", tags=["crops"])


class CropCreate(BaseModel):
    field_id: int
    crop_type: str
    variety: str | None = None
    planting_date: date | None = None
    status: str | None = None


class CropRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    crop_type: str
    variety: str | None = None
    planting_date: date | None = None
    status: str | None = None
    created_at: datetime


@router.get("", response_model=list[CropRead])
def list_crops(farm_id: int | None = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Crop)
    if farm_id is not None:
        query = query.join(models.Field).filter(models.Field.farm_id == farm_id)
    return query.all()


@router.get("/{crop_id}", response_model=CropRead)
def get_crop(crop_id: int, db: Session = Depends(get_db)):
    crop = db.query(models.Crop).filter(models.Crop.id == crop_id).first()
    if not crop:
        raise AppError(404, "crop_not_found", "That crop no longer exists.")
    return crop


@router.post("", response_model=CropRead)
def create_crop(payload: CropCreate, db: Session = Depends(get_db)):
    crop = models.Crop(**payload.model_dump())
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop
