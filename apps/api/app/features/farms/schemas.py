from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class FarmIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    region: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_hectares: float | None = Field(default=None, gt=0)


class FarmUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    region: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_hectares: float | None = Field(default=None, gt=0)


class FarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    region: str | None
    latitude: float | None
    longitude: float | None
    area_hectares: float | None
    created_at: datetime


class PlantingStage(BaseModel):
    id: int
    crop_type: str
    variety: str | None
    planting_date: date | None
    status: str | None
    stage: str | None
    days_since_planting: int | None


class FieldOverview(BaseModel):
    id: int
    name: str
    area_hectares: float | None
    plantings: list[PlantingStage]


class FarmOverview(BaseModel):
    farm: FarmOut
    fields: list[FieldOverview]


class RiskOut(BaseModel):
    id: str
    title: str
    severity: str
    urgency: str
    reason: str
    facts: list[str]
    source: str
    crop: str
    field: str
    planting_id: int


class Plot(BaseModel):
    planting_id: int
    crop: str
    field: str
    # relative size for the field mosaic: the field's area split between its plantings
    share: float


class FarmSummary(BaseModel):
    id: int
    name: str
    region: str | None
    area_hectares: float | None
    plots: list[Plot]
    risks: list[RiskOut]
    last_logged_at: datetime | None


class PlantingProgress(BaseModel):
    id: int
    crop: str
    variety: str | None
    stage: str
    day: int | None
    cycle_days: int
    # 0..1 through the crop's calendar, for the stage bar
    progress: float | None
    harvest_start: date | None
    harvest_end: date | None


class FieldState(BaseModel):
    id: int
    name: str
    area_hectares: float | None
    soil_type: str | None
    plantings: list[PlantingProgress]


class RainDay(BaseModel):
    day: date
    mm: float | None


class LogOut(BaseModel):
    id: int
    field: str
    obs_type: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    observed_at: datetime


class FarmDashboard(BaseModel):
    farm: FarmOut
    fields: list[FieldState]
    rainfall: list[RainDay]
    risks: list[RiskOut]
    recent_logs: list[LogOut]
