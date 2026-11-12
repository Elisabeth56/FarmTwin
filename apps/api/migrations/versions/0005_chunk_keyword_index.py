"""FTS5 keyword index over chunk titles and text for hybrid retrieval (ADR-018).

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE VIRTUAL TABLE document_chunks_fts USING fts5(chunk_title, content)")
    op.execute(
        "INSERT INTO document_chunks_fts(rowid, chunk_title, content) "
        "SELECT id, coalesce(chunk_title, ''), content FROM document_chunks"
    )


def downgrade() -> None:
    op.execute("DROP TABLE document_chunks_fts")
