from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/api/farms", tags=["farms"])


class FarmCreate(BaseModel):
    name: str
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    area_hectares: float | None = None


class FarmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    area_hectares: float | None = None
    created_at: datetime


@router.get("", response_model=list[FarmRead])
def list_farms(db: Session = Depends(get_db)):
    return db.query(models.Farm).all()


@router.get("/{farm_id}", response_model=FarmRead)
def get_farm(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(models.Farm).filter(models.Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(404, "not found")
    return farm


@router.post("", response_model=FarmRead)
def create_farm(payload: FarmCreate, db: Session = Depends(get_db)):
    farm = models.Farm(**payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm
