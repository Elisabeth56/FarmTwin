"""Database models. Typed SQLAlchemy 2.0 mappings; the table shapes match v1 exactly."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    area_hectares: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    fields: Mapped[list["Field"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    weather_snapshots: Mapped[list["WeatherSnapshot"]] = relationship(
        back_populates="farm", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="farm", cascade="all, delete-orphan"
    )


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    area_hectares: Mapped[float | None] = mapped_column(Float)
    soil_type: Mapped[str | None] = mapped_column(String)
    soil_ph_estimate: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    farm: Mapped["Farm"] = relationship(back_populates="fields")
    crops: Mapped[list["Crop"]] = relationship(back_populates="field", cascade="all, delete-orphan")
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="field", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="field")


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"), index=True)
    crop_type: Mapped[str] = mapped_column(String)
    variety: Mapped[str | None] = mapped_column(String)
    planting_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    field: Mapped["Field"] = relationship(back_populates="crops")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"), index=True)
    obs_type: Mapped[str] = mapped_column(String)
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String)
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    field: Mapped["Field"] = relationship(back_populates="observations")


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    temp_min_c: Mapped[float | None] = mapped_column(Float)
    temp_max_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    farm: Mapped["Farm"] = relationship(back_populates="weather_snapshots")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    field_id: Mapped[int | None] = mapped_column(ForeignKey("fields.id"), index=True)
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str | None] = mapped_column(Text)
    when_urgency: Mapped[str | None] = mapped_column(String)
    risk_if_ignored: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int | None] = mapped_column(Integer)
    cited_chunk_ids: Mapped[str | None] = mapped_column(Text)  # JSON list of chunk ids
    model_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    farm: Mapped["Farm"] = relationship(back_populates="recommendations")
    field: Mapped["Field | None"] = relationship(back_populates="recommendations")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String, index=True)
    source_title: Mapped[str | None] = mapped_column(String)
    source_org: Mapped[str | None] = mapped_column(String, index=True)
    source_url: Mapped[str | None] = mapped_column(String)
    source_note: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String, index=True)
    crop: Mapped[str | None] = mapped_column(String, index=True)
    topics: Mapped[str | None] = mapped_column(Text)  # JSON list
    chunk_title: Mapped[str | None] = mapped_column(String)
    token_count: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
