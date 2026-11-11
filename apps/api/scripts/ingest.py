"""FarmTwin corpus ingestion.

Syncs `knowledge/corpus/*.md` into `document_chunks` and its sqlite-vec sibling.
Chunks are keyed by content hash: unchanged chunks are left alone, edited or new
ones are embedded, and chunks no longer in the corpus are removed. Running it
twice in a row embeds nothing the second time.

If the configured embedder differs from the one that built the index, everything is
re-embedded. Run from apps/api after `scripts/fetch_embedder.py`:

    uv run python scripts/ingest.py
"""

import json
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.db import models
from app.db.migrate import run_migrations
from app.db.session import SessionLocal
from app.rag.corpus import CorpusChunk, load_corpus, plan_sync
from app.rag.embedder import embed_passages
from app.rag.index_meta import record_embedder, stored_embedder

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


def main() -> int:
    corpus_dir = get_settings().knowledge_dir / "corpus"
    if not corpus_dir.exists():
        print(f"ERROR: corpus dir not found at {corpus_dir}", file=sys.stderr)
        return 1

    run_migrations()
    chunks = load_corpus(corpus_dir)
    print(f"Read {len(chunks)} chunks from {corpus_dir}")

    session = SessionLocal()
    # raw vec-table writes share the session's connection; a second sqlite
    # connection on the same file would deadlock
    cur = session.connection().connection.cursor()
    try:
        cur.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_vec USING vec0("
            f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{EMBED_DIM}])"
        )
        existing = dict(session.query(models.DocumentChunk.id, models.DocumentChunk.content_hash).all())
        embedder = get_settings().embedder_model
        if stored_embedder(session) != embedder:
            # vectors from another embedder can't be compared with new ones; rebuild them all
            existing = dict.fromkeys(existing)
        to_add, to_delete = plan_sync(existing, chunks)

        # remove stale rows first so their vectors never outlive them
        for row_id in to_delete:
            cur.execute("DELETE FROM document_chunks_vec WHERE chunk_id = ?", (row_id,))
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
        record_embedder(session, embedder)
        session.commit()
    finally:
        session.close()

    by_crop = Counter(c.frontmatter.get("crop") or "(none)" for c in chunks)
    print(f"Added {len(to_add)}, removed {len(to_delete)}, unchanged {len(chunks) - len(to_add)}")
    print("Chunks by crop: " + ", ".join(f"{crop} {n}" for crop, n in sorted(by_crop.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
