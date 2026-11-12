"""Everything the farm screen shows, in one call: fields with stage progress, 14 days of
rainfall, the risks firing now and the latest logs."""

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.lookup import farm_or_404
from app.engines.farm_state import PlantingState, latest_weather, planting_states
from app.features.farms.schemas import (
    FarmDashboard,
    FarmOut,
    FieldState,
    LogOut,
    PlantingProgress,
    RainDay,
)
from app.features.farms.summary import risks_of

RAIN_DAYS = 14
RECENT_LOGS = 8


def dashboard(db: Session, farm_id: int, today: date | None = None) -> FarmDashboard:
    today = today or date.today()
    farm = farm_or_404(db, farm_id)
    states = planting_states(db, farm, latest_weather(db, farm.id), today)
    by_field: dict[int, list[PlantingProgress]] = defaultdict(list)
    for s in states:
        by_field[s.field.id].append(_progress(s))

    return FarmDashboard(
        farm=FarmOut.model_validate(farm),
        fields=[
            FieldState(
                id=f.id,
                name=f.name,
                area_hectares=f.area_hectares,
                soil_type=f.soil_type,
                plantings=by_field.get(f.id, []),
            )
            for f in sorted(farm.fields, key=lambda f: f.id)
        ],
        rainfall=_rainfall(db, farm, today),
        risks=risks_of(states),
        recent_logs=_recent_logs(db, farm.id),
    )


def _progress(s: PlantingState) -> PlantingProgress:
    stage = s.stage
    total = stage["total_cycle_days"]
    day = stage["days_since_planting"]
    window = stage["expected_harvest_range"]
    progress = min(max(day / total, 0.0), 1.0) if total and day is not None else None
    return PlantingProgress(
        id=s.planting.id,
        crop=s.planting.crop_type,
        variety=s.planting.variety,
        stage=stage["stage"],
        day=day,
        cycle_days=total,
        progress=progress,
        harvest_start=window[0] if window else None,
        harvest_end=window[1] if window else None,
    )


def _rainfall(db: Session, farm: models.Farm, today: date) -> list[RainDay]:
    """Daily rain for the last 14 days. Field logs win; a weather snapshot fills days with no log."""
    start = today - timedelta(days=RAIN_DAYS - 1)
    logged: dict[date, float] = defaultdict(float)
    rows = db.scalars(
        select(models.Observation)
        .join(models.Field)
        .where(
            models.Field.farm_id == farm.id,
            models.Observation.obs_type == "rainfall",
            models.Observation.observed_at >= datetime.combine(start, datetime.min.time()),
        )
    ).all()
    for o in rows:
        if o.value_numeric is not None:
            # several fields may log the same storm; the farm's rain for the day is the largest reading
            day = o.observed_at.date()
            logged[day] = max(logged[day], o.value_numeric)
    snapshots = {
        w.snapshot_date: w.rainfall_mm
        for w in farm.weather_snapshots
        if w.snapshot_date >= start and w.rainfall_mm is not None
    }
    days = [start + timedelta(days=i) for i in range(RAIN_DAYS)]
    return [RainDay(day=d, mm=logged[d] if d in logged else snapshots.get(d)) for d in days]


def _recent_logs(db: Session, farm_id: int) -> list[LogOut]:
    rows = db.execute(
        select(models.Observation, models.Field.name)
        .join(models.Field)
        .where(models.Field.farm_id == farm_id)
        .order_by(models.Observation.observed_at.desc(), models.Observation.id.desc())
        .limit(RECENT_LOGS)
    ).all()
    return [
        LogOut(
            id=o.id,
            field=name,
            obs_type=o.obs_type,
            value_numeric=o.value_numeric,
            value_text=o.value_text,
            unit=o.unit,
            observed_at=o.observed_at,
        )
        for o, name in rows
    ]
