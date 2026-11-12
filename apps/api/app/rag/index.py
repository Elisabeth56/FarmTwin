"""Keeps the search index in step with knowledge/corpus (ADR-016, ADR-018).

Chunks are keyed by content hash: unchanged chunks are left alone, edited or new ones are
embedded, and chunks no longer in the corpus are removed. If the configured embedder isn't the
one that built the index, everything is re-embedded. The API runs this at startup, so an app
update that ships new guides or a new embedder brings the index along by itself.
"""

import json
import logging
import struct
from dataclasses import dataclass

from app.config import get_settings
from app.db import models
from app.db.session import SessionLocal
from app.rag.corpus import CorpusChunk, load_corpus, plan_sync
from app.rag.embedder import embed_passages
from app.rag.index_meta import record_embedder, stored_embedder

logger = logging.getLogger(__name__)

EMBED_DIM = 384  # bge-small-en-v1.5


def vec_to_blob(vec) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def chunk_row(chunk: CorpusChunk) -> models.DocumentChunk:
    fm = chunk.frontmatter
    topics = fm.get("topics") or []
    if not isinstance(topics, list):
        topics = [str(topics)]
    return models.DocumentChunk(
        source_id=fm.get("source_id"),
        source_title=fm.get("source_title"),
        source_org=fm.get("source_org"),
        source_url=fm.get("source_url"),
        source_note=fm.get("source_note"),
        region=fm.get("region"),
        crop=fm.get("crop"),
        topics=json.dumps(topics),
        chunk_title=chunk.title,
        token_count=len(chunk.content.split()),
        content=chunk.content,
        content_hash=chunk.content_hash,
    )


@dataclass
class SyncResult:
    chunks: int
    added: int
    removed: int


def sync_index() -> SyncResult:
    chunks = load_corpus(get_settings().knowledge_dir / "corpus")
    session = SessionLocal()
    # raw vec-table writes share the session's connection; a second sqlite
    # connection on the same file would deadlock
    cur = session.connection().connection.cursor()
    try:
        cur.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_vec USING vec0("
            f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{EMBED_DIM}])"
        )
        rows = session.query(models.DocumentChunk.id, models.DocumentChunk.content_hash).all()
        existing: dict[int, str | None] = {row_id: content_hash for row_id, content_hash in rows}
        embedder = get_settings().embedder_model
        if stored_embedder(session) != embedder:
            # vectors from another embedder can't be compared with new ones; rebuild them all
            existing = {row_id: None for row_id in existing}
        to_add, to_delete = plan_sync(existing, chunks)

        # remove stale rows first so their vectors never outlive them
        for row_id in to_delete:
            cur.execute("DELETE FROM document_chunks_vec WHERE chunk_id = ?", (row_id,))
            cur.execute("DELETE FROM document_chunks_fts WHERE rowid = ?", (row_id,))
        if to_delete:
            session.query(models.DocumentChunk).filter(models.DocumentChunk.id.in_(to_delete)).delete()

        if to_add:
            # embed the title with the body so short chunks still carry their topic
            embeddings = embed_passages(f"{c.title or ''}\n{c.content}" for c in to_add)
            for chunk, emb in zip(to_add, embeddings, strict=True):
                row = chunk_row(chunk)
                session.add(row)
                session.flush()
                cur.execute(
                    "INSERT INTO document_chunks_vec(chunk_id, embedding) VALUES (?, ?)",
                    (row.id, vec_to_blob(emb)),
                )
                cur.execute(
                    "INSERT INTO document_chunks_fts(rowid, chunk_title, content) VALUES (?, ?, ?)",
                    (row.id, chunk.title or "", chunk.content),
                )
        record_embedder(session, embedder)
        session.commit()
    finally:
        session.close()
    result = SyncResult(len(chunks), len(to_add), len(to_delete))
    logger.info("index synced chunks=%s added=%s removed=%s", result.chunks, result.added, result.removed)
    return result
