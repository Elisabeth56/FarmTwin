"""Observations logged against a field: rainfall, humidity, temperature, pests, disease, notes."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.lookup import farm_or_404, field_or_404, get_or_404
from app.db.session import get_db

router = APIRouter(prefix="/api/observations", tags=["observations"])

ObsType = Literal["rainfall", "humidity", "temperature", "pest", "disease", "note"]


class ObservationIn(BaseModel):
    field_id: int
    obs_type: ObsType
    value_numeric: float | None = Field(default=None, ge=0)
    value_text: str | None = None
    unit: str | None = None
    observed_at: datetime


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    obs_type: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    observed_at: datetime
    created_at: datetime


@router.get("", response_model=list[ObservationOut])
def list_observations(farm_id: int = Query(...), db: Session = Depends(get_db)):
    farm_or_404(db, farm_id)
    return db.scalars(
        select(models.Observation)
        .join(models.Field)
        .where(models.Field.farm_id == farm_id)
        .order_by(models.Observation.observed_at.desc())
    ).all()


@router.post("", response_model=ObservationOut, status_code=201)
def create_observation(body: ObservationIn, db: Session = Depends(get_db)):
    field_or_404(db, body.field_id)
    obs = models.Observation(**body.model_dump())
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


@router.get("/{observation_id}", response_model=ObservationOut)
def get_observation(observation_id: int, db: Session = Depends(get_db)):
    return get_or_404(
        db, models.Observation, observation_id, "observation_not_found", "That observation no longer exists."
    )


@router.delete("/{observation_id}", status_code=204)
def delete_observation(observation_id: int, db: Session = Depends(get_db)):
    """Used by the dashboard's undo after logging."""
    obs = get_or_404(
        db, models.Observation, observation_id, "observation_not_found", "That observation no longer exists."
    )
    db.delete(obs)
    db.commit()
    return Response(status_code=204)
