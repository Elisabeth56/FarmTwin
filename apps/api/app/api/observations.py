from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.errors import AppError

router = APIRouter(prefix="/api/observations", tags=["observations"])

ObsType = Literal["rainfall", "humidity", "temperature", "pest", "disease", "note"]


class ObservationCreate(BaseModel):
    field_id: int
    obs_type: ObsType
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    observed_at: datetime


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    obs_type: str
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    observed_at: datetime
    created_at: datetime


@router.get("", response_model=list[ObservationRead])
def list_observations(farm_id: int | None = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Observation)
    if farm_id is not None:
        query = query.join(models.Field).filter(models.Field.farm_id == farm_id)
    return query.all()


@router.get("/{observation_id}", response_model=ObservationRead)
def get_observation(observation_id: int, db: Session = Depends(get_db)):
    obs = db.query(models.Observation).filter(models.Observation.id == observation_id).first()
    if not obs:
        raise AppError(404, "observation_not_found", "That observation no longer exists.")
    return obs


@router.post("", response_model=ObservationRead)
def create_observation(payload: ObservationCreate, db: Session = Depends(get_db)):
    obs = models.Observation(**payload.model_dump())
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs
