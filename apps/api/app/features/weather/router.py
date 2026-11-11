"""Daily weather snapshots for a farm."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.lookup import farm_or_404, get_or_404
from app.db.session import get_db

router = APIRouter(prefix="/api/weather", tags=["weather"])


class WeatherIn(BaseModel):
    farm_id: int
    snapshot_date: date
    rainfall_mm: float | None = Field(default=None, ge=0)
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class WeatherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    snapshot_date: date
    rainfall_mm: float | None
    temp_min_c: float | None
    temp_max_c: float | None
    humidity_pct: float | None
    notes: str | None


@router.get("", response_model=list[WeatherOut])
def list_weather(farm_id: int = Query(...), db: Session = Depends(get_db)):
    farm_or_404(db, farm_id)
    return db.scalars(
        select(models.WeatherSnapshot)
        .where(models.WeatherSnapshot.farm_id == farm_id)
        .order_by(models.WeatherSnapshot.snapshot_date.desc())
    ).all()


@router.post("", response_model=WeatherOut, status_code=201)
def create_weather(body: WeatherIn, db: Session = Depends(get_db)):
    farm_or_404(db, body.farm_id)
    snapshot = models.WeatherSnapshot(**body.model_dump())
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/{snapshot_id}", response_model=WeatherOut)
def get_weather(snapshot_id: int, db: Session = Depends(get_db)):
    return get_or_404(
        db, models.WeatherSnapshot, snapshot_id, "weather_not_found", "That weather record no longer exists."
    )
