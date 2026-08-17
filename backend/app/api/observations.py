from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/api/observations", tags=["observations"])

ObsType = Literal["rainfall", "humidity", "temperature", "pest", "disease", "note"]


class ObservationCreate(BaseModel):
    field_id: int
    obs_type: ObsType
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    observed_at: datetime


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    obs_type: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    observed_at: datetime
    created_at: datetime


@router.get("", response_model=list[ObservationRead])
def list_observations(
    farm_id: Optional[int] = Query(None), db: Session = Depends(get_db)
):
    query = db.query(models.Observation)
    if farm_id is not None:
        query = query.join(models.Field).filter(models.Field.farm_id == farm_id)
    return query.all()


@router.get("/{observation_id}", response_model=ObservationRead)
def get_observation(observation_id: int, db: Session = Depends(get_db)):
    obs = (
        db.query(models.Observation)
        .filter(models.Observation.id == observation_id)
        .first()
    )
    if not obs:
        raise HTTPException(404, "not found")
    return obs


@router.post("", response_model=ObservationRead)
def create_observation(payload: ObservationCreate, db: Session = Depends(get_db)):
    obs = models.Observation(**payload.model_dump())
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs
