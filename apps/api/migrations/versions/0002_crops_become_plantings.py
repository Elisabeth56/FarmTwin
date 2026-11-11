"""crops become plantings: a field can hold several at once (ADR-019).

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("crops", "plantings")


def downgrade() -> None:
    op.rename_table("plantings", "crops")
