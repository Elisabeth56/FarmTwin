"""v1 baseline: the tables the hackathon build created with create_all.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "farms",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("region", sa.String),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("area_hectares", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "fields",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("farm_id", sa.Integer, sa.ForeignKey("farms.id"), nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("area_hectares", sa.Float),
        sa.Column("soil_type", sa.String),
        sa.Column("soil_ph_estimate", sa.Float),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "crops",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("field_id", sa.Integer, sa.ForeignKey("fields.id"), nullable=False, index=True),
        sa.Column("crop_type", sa.String, nullable=False),
        sa.Column("variety", sa.String),
        sa.Column("planting_date", sa.Date),
        sa.Column("status", sa.String),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "observations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("field_id", sa.Integer, sa.ForeignKey("fields.id"), nullable=False, index=True),
        sa.Column("obs_type", sa.String, nullable=False),
        sa.Column("value_numeric", sa.Float),
        sa.Column("value_text", sa.Text),
        sa.Column("unit", sa.String),
        sa.Column("observed_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("farm_id", sa.Integer, sa.ForeignKey("farms.id"), nullable=False, index=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("rainfall_mm", sa.Float),
        sa.Column("temp_min_c", sa.Float),
        sa.Column("temp_max_c", sa.Float),
        sa.Column("humidity_pct", sa.Float),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("farm_id", sa.Integer, sa.ForeignKey("farms.id"), nullable=False, index=True),
        sa.Column("field_id", sa.Integer, sa.ForeignKey("fields.id"), index=True),
        sa.Column("what", sa.Text, nullable=False),
        sa.Column("why", sa.Text),
        sa.Column("when_urgency", sa.String),
        sa.Column("risk_if_ignored", sa.Text),
        sa.Column("priority", sa.Integer),
        sa.Column("cited_chunk_ids", sa.Text),
        sa.Column("model_name", sa.String),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("source_id", sa.String, index=True),
        sa.Column("source_title", sa.String),
        sa.Column("source_org", sa.String, index=True),
        sa.Column("source_url", sa.String),
        sa.Column("source_note", sa.Text),
        sa.Column("region", sa.String, index=True),
        sa.Column("crop", sa.String, index=True),
        sa.Column("topics", sa.Text),
        sa.Column("chunk_title", sa.String),
        sa.Column("token_count", sa.Integer),
        sa.Column("content", sa.Text, nullable=False),
    )


def downgrade() -> None:
    for table in [
        "document_chunks",
        "recommendations",
        "weather_snapshots",
        "observations",
        "crops",
        "fields",
        "farms",
    ]:
        op.drop_table(table)
