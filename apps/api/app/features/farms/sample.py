"""A sample farm for exploring the app before entering real data. Dates are relative to today so
its stages and risks always look current. The readings are made up and the farm is named so."""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db import models

SAMPLE_NAME = "Sample farm"


def create_sample_farm(db: Session, today: date | None = None) -> models.Farm:
    today = today or date.today()

    def days_ago(n: int) -> date:
        return today - timedelta(days=n)

    def logged(n: int) -> datetime:
        return datetime.combine(days_ago(n), datetime.min.time()).replace(hour=8)

    farm = models.Farm(name=SAMPLE_NAME, region="Zaria, Kaduna", area_hectares=2.1)
    main = models.Field(name="Main field", area_hectares=1.0, soil_type="sandy loam")
    east = models.Field(name="East plot", area_hectares=0.6, soil_type="sandy loam")
    back = models.Field(name="Back plot", area_hectares=0.5, soil_type="loam")
    farm.fields = [main, east, back]

    main.plantings = [
        models.Planting(crop_type="maize", variety="SAMMAZ 15", planting_date=days_ago(38), status="active")
    ]
    east.plantings = [models.Planting(crop_type="cowpea", planting_date=days_ago(40), status="active")]
    back.plantings = [
        models.Planting(
            crop_type="sorghum", variety="SAMSORG 14", planting_date=days_ago(12), status="active"
        )
    ]

    main.observations = [
        models.Observation(obs_type="rainfall", value_numeric=62, unit="mm", observed_at=logged(2)),
        models.Observation(obs_type="rainfall", value_numeric=18, unit="mm", observed_at=logged(6)),
    ]
    east.observations = [
        models.Observation(
            obs_type="pest", value_text="Small insects inside the flowers", observed_at=logged(1)
        ),
    ]
    farm.weather_snapshots = [
        models.WeatherSnapshot(
            snapshot_date=days_ago(1), rainfall_mm=12, humidity_pct=86, temp_min_c=22, temp_max_c=31
        ),
    ]
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm
