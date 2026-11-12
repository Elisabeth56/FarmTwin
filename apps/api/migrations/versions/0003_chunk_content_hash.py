"""document chunks get a content hash so ingest only re-embeds what changed.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch:
        batch.add_column(sa.Column("content_hash", sa.String(64)))
        batch.create_index("ix_document_chunks_content_hash", ["content_hash"])


def downgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch:
        batch.drop_index("ix_document_chunks_content_hash")
        batch.drop_column("content_hash")
