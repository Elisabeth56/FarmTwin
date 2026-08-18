from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    area_hectares = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    fields = relationship("Field", back_populates="farm", cascade="all, delete-orphan")
    weather_snapshots = relationship(
        "WeatherSnapshot", back_populates="farm", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "Recommendation", back_populates="farm", cascade="all, delete-orphan"
    )


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    area_hectares = Column(Float, nullable=True)
    soil_type = Column(String, nullable=True)
    soil_ph_estimate = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    farm = relationship("Farm", back_populates="fields")
    crops = relationship("Crop", back_populates="field", cascade="all, delete-orphan")
    observations = relationship(
        "Observation", back_populates="field", cascade="all, delete-orphan"
    )
    recommendations = relationship("Recommendation", back_populates="field")


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    crop_type = Column(String, nullable=False)
    variety = Column(String, nullable=True)
    planting_date = Column(Date, nullable=True)
    status = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    field = relationship("Field", back_populates="crops")


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    obs_type = Column(String, nullable=False)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    unit = Column(String, nullable=True)
    observed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    field = relationship("Field", back_populates="observations")


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    rainfall_mm = Column(Float, nullable=True)
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    farm = relationship("Farm", back_populates="weather_snapshots")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=True, index=True)
    what = Column(Text, nullable=False)
    why = Column(Text, nullable=True)
    when_urgency = Column(String, nullable=True)
    risk_if_ignored = Column(Text, nullable=True)
    priority = Column(Integer, nullable=True)
    cited_chunk_ids = Column(Text, nullable=True)  # JSON string
    model_name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    farm = relationship("Farm", back_populates="recommendations")
    field = relationship("Field", back_populates="recommendations")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, nullable=True, index=True)
    source_title = Column(String, nullable=True)
    source_org = Column(String, nullable=True, index=True)
    source_url = Column(String, nullable=True)
    source_note = Column(Text, nullable=True)
    region = Column(String, nullable=True, index=True)
    crop = Column(String, nullable=True, index=True)
    topics = Column(Text, nullable=True)  # JSON string
    chunk_title = Column(String, nullable=True)
    token_count = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
