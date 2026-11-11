"""What the farm list shows for each farm: its plots, the risks firing now, and when it was last logged."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import models
from app.engines.farm_state import PlantingState, latest_weather, planting_states
from app.features.farms.schemas import FarmSummary, Plot, RiskOut

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def summaries(db: Session, today: date | None = None) -> list[FarmSummary]:
    today = today or date.today()
    farms = db.scalars(
        select(models.Farm)
        .options(selectinload(models.Farm.fields).selectinload(models.Field.plantings))
        .order_by(models.Farm.name)
    ).all()
    rows = db.execute(
        select(models.Field.farm_id, func.max(models.Observation.created_at))
        .join(models.Observation, models.Observation.field_id == models.Field.id)
        .group_by(models.Field.farm_id)
    ).all()
    last_logged = {farm_id: at for farm_id, at in rows}
    out = []
    for farm in farms:
        states = planting_states(db, farm, latest_weather(db, farm.id), today)
        out.append(
            FarmSummary(
                id=farm.id,
                name=farm.name,
                region=farm.region,
                area_hectares=farm.area_hectares,
                plots=_plots(states),
                risks=risks_of(states),
                last_logged_at=last_logged.get(farm.id),
            )
        )
    return out


def risks_of(states: list[PlantingState]) -> list[RiskOut]:
    """Every firing risk, most severe first."""
    risks = [
        RiskOut(
            id=r.name,
            title=r.title,
            severity=r.severity,
            urgency=r.time_sensitivity,
            reason=r.reason,
            facts=r.supporting_facts,
            source=r.source,
            crop=s.planting.crop_type,
            field=s.field.name,
            planting_id=s.planting.id,
        )
        for s in states
        for r in s.risks
    ]
    return sorted(risks, key=lambda r: SEVERITY_ORDER.get(r.severity, 3))


def _plots(states: list[PlantingState]) -> list[Plot]:
    per_field: dict[int, int] = {}
    for s in states:
        per_field[s.field.id] = per_field.get(s.field.id, 0) + 1
    return [
        Plot(
            planting_id=s.planting.id,
            crop=s.planting.crop_type,
            field=s.field.name,
            share=round((s.field.area_hectares or 1.0) / per_field[s.field.id], 3),
        )
        for s in states
    ]
