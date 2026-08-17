from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/api/weather", tags=["weather"])


class WeatherSnapshotCreate(BaseModel):
    farm_id: int
    snapshot_date: date
    rainfall_mm: Optional[float] = None
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    notes: Optional[str] = None


class WeatherSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    snapshot_date: date
    rainfall_mm: Optional[float] = None
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    notes: Optional[str] = None


@router.get("", response_model=list[WeatherSnapshotRead])
def list_weather(
    farm_id: Optional[int] = Query(None), db: Session = Depends(get_db)
):
    query = db.query(models.WeatherSnapshot)
    if farm_id is not None:
        query = query.filter(models.WeatherSnapshot.farm_id == farm_id)
    return query.all()


@router.get("/{snapshot_id}", response_model=WeatherSnapshotRead)
def get_weather(snapshot_id: int, db: Session = Depends(get_db)):
    snap = (
        db.query(models.WeatherSnapshot)
        .filter(models.WeatherSnapshot.id == snapshot_id)
        .first()
    )
    if not snap:
        raise HTTPException(404, "not found")
    return snap


@router.post("", response_model=WeatherSnapshotRead)
def create_weather(payload: WeatherSnapshotCreate, db: Session = Depends(get_db)):
    snap = models.WeatherSnapshot(**payload.model_dump())
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap
