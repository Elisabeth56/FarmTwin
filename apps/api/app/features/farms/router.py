"""Farms: CRUD plus an overview of every field and active planting with its stage."""

from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import models
from app.db.lookup import farm_or_404
from app.db.session import get_db
from app.engines.crop_calendar import compute_growth_stage
from app.features.farms.schemas import (
    FarmIn,
    FarmOut,
    FarmOverview,
    FarmUpdate,
    FieldOverview,
    PlantingStage,
)

router = APIRouter(prefix="/api/farms", tags=["farms"])


@router.get("", response_model=list[FarmOut])
def list_farms(db: Session = Depends(get_db)):
    return db.scalars(select(models.Farm).order_by(models.Farm.name)).all()


@router.post("", response_model=FarmOut, status_code=201)
def create_farm(body: FarmIn, db: Session = Depends(get_db)):
    farm = models.Farm(**body.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(farm_id: int, db: Session = Depends(get_db)):
    return farm_or_404(db, farm_id)


@router.patch("/{farm_id}", response_model=FarmOut)
def update_farm(farm_id: int, body: FarmUpdate, db: Session = Depends(get_db)):
    farm = farm_or_404(db, farm_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(farm, key, value)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=204)
def delete_farm(farm_id: int, db: Session = Depends(get_db)):
    db.delete(farm_or_404(db, farm_id))
    db.commit()
    return Response(status_code=204)


@router.get("/{farm_id}/overview", response_model=FarmOverview)
def farm_overview(farm_id: int, db: Session = Depends(get_db)):
    """The farm with each field and its active plantings, stage computed for today."""
    farm = farm_or_404(db, farm_id)
    fields = db.scalars(
        select(models.Field)
        .where(models.Field.farm_id == farm.id)
        .options(selectinload(models.Field.plantings))
        .order_by(models.Field.id)
    ).all()
    today = date.today()
    return FarmOverview(
        farm=FarmOut.model_validate(farm),
        fields=[
            FieldOverview(
                id=f.id,
                name=f.name,
                area_hectares=f.area_hectares,
                plantings=[_with_stage(p, today) for p in f.plantings if p.status in (None, "active")],
            )
            for f in fields
        ],
    )


def _with_stage(planting: models.Planting, today: date) -> PlantingStage:
    stage = days = None
    if planting.planting_date:
        days = (today - planting.planting_date).days
        try:
            stage = compute_growth_stage(planting.crop_type, planting.planting_date, today)["stage"]
        except ValueError:
            stage = None  # no calendar for this crop yet; the crop engine adds them (#8, #9)
    return PlantingStage(
        id=planting.id,
        crop_type=planting.crop_type,
        variety=planting.variety,
        planting_date=planting.planting_date,
        status=planting.status,
        stage=stage,
        days_since_planting=days,
    )
