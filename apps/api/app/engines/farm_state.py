"""A farm's current state: each active planting with its stage and the risks that fire for it.
Used by the farm list, the dashboard and /api/ask, so all three agree."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.engines.rules import RiskFlag, evaluate, growth_stage

OBSERVATION_DAYS = 30
MAX_OBSERVATIONS = 12


@dataclass
class PlantingState:
    planting: models.Planting
    field: models.Field
    stage: dict[str, Any]
    risks: list[RiskFlag]


def planting_states(db: Session, farm: models.Farm, weather: dict | None, today: date) -> list[PlantingState]:
    """Each active planting gets its own stage, and risks from its own field's readings."""
    states: list[PlantingState] = []
    for field in farm.fields:
        observations = recent_observations(db, field.id, today)
        for planting in field.plantings:
            if planting.status != "active":
                continue
            stage = stage_for(planting, today)
            risks = evaluate(planting.crop_type, stage["stage"], observations, weather, today)
            states.append(PlantingState(planting, field, stage, risks))
    return states


def stage_for(planting: models.Planting, today: date) -> dict[str, Any]:
    planted = planting.planting_date
    if planted is not None:
        try:
            return growth_stage(planting.crop_type, planted, today)
        except ValueError:
            pass  # crop without a rule file: everything still works, just without a calendar
    return {
        "stage": "unknown",
        "days_since_planting": (today - planted).days if planted else None,
        "total_cycle_days": 0,
        "expected_harvest_range": None,
        "description": "",
    }


def recent_observations(db: Session, field_id: int, today: date) -> list[dict]:
    since = datetime.combine(today - timedelta(days=OBSERVATION_DAYS), datetime.min.time())
    rows = (
        db.query(models.Observation)
        .filter(models.Observation.field_id == field_id, models.Observation.observed_at >= since)
        .order_by(models.Observation.observed_at.desc())
        .limit(MAX_OBSERVATIONS)
        .all()
    )
    return [
        {
            "obs_type": o.obs_type,
            "value_numeric": o.value_numeric,
            "value_text": o.value_text,
            "unit": o.unit,
            "observed_at": o.observed_at.date(),
        }
        for o in rows
    ]


def latest_weather(db: Session, farm_id: int) -> dict | None:
    row = (
        db.query(models.WeatherSnapshot)
        .filter(models.WeatherSnapshot.farm_id == farm_id)
        .order_by(models.WeatherSnapshot.snapshot_date.desc())
        .first()
    )
    if row is None:
        return None
    return {
        "snapshot_date": row.snapshot_date,
        "rainfall_mm": row.rainfall_mm,
        "humidity_pct": row.humidity_pct,
        "temp_min_c": row.temp_min_c,
        "temp_max_c": row.temp_max_c,
    }
