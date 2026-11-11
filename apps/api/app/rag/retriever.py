"""Production retrieval for FarmTwin.

- Embeds queries with a module-level SentenceTransformer (loaded once).
- Runs KNN against the sqlite-vec virtual table `document_chunks_vec`.
- Joins to `document_chunks` for metadata and returns dicts.
"""

from __future__ import annotations

import json
import struct
from typing import Any, Iterable, Optional

from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


_EMBEDDER_MODEL_NAME = "all-MiniLM-L6-v2"

print(f"[retriever] Loading embedder {_EMBEDDER_MODEL_NAME} (one-time)...")
_EMBEDDER = SentenceTransformer(_EMBEDDER_MODEL_NAME)
print(f"[retriever] Embedder ready, dim={_EMBEDDER.get_sentence_embedding_dimension()}")


def _vec_to_blob(vec: Iterable[float]) -> bytes:
    vec_list = list(vec)
    return struct.pack(f"{len(vec_list)}f", *vec_list)


def build_query(
    crop_type: str,
    growth_stage: str,
    region: str,
    risk_flags: list,
    user_question: str,
) -> str:
    """Compose a compact retrieval query (< 40 words)."""
    risk_names: list[str] = []
    for f in risk_flags or []:
        name = getattr(f, "name", None) or (f.get("name") if isinstance(f, dict) else None)
        if name:
            risk_names.append(name.replace("_", " "))
    risk_str = " ".join(risk_names[:3])

    q = " ".join(
        p for p in [
            crop_type or "",
            growth_stage or "",
            region or "",
            risk_str,
            user_question or "",
        ] if p
    )
    words = q.split()
    if len(words) > 40:
        words = words[:40]
    return " ".join(words)


def retrieve_chunks(
    query: str,
    top_k: int = 6,
    db_session: Optional[Session] = None,
) -> list[dict]:
    """Embed the query and return top-k matching chunks with metadata.

    Uses the SQLAlchemy session's DBAPI connection (which has sqlite-vec loaded
    via the engine's connect event) so we do not open a second sqlite
    connection to the same file (Day 2 lock fix).
    """
    if not query or not query.strip():
        return []

    owns_session = db_session is None
    session = db_session or SessionLocal()
    try:
        qvec = _EMBEDDER.encode(query, normalize_embeddings=True).tolist()
        blob = _vec_to_blob(qvec)

        dbapi_conn = session.connection().connection
        cur = dbapi_conn.cursor()
        try:
            rows = cur.execute(
                """
                SELECT
                    dc.id, dc.source_org, dc.source_title, dc.chunk_title,
                    dc.content, dc.region, dc.crop, dc.topics,
                    v.distance
                FROM document_chunks_vec v
                JOIN document_chunks dc ON dc.id = v.chunk_id
                WHERE v.embedding MATCH ? AND k = ?
                ORDER BY v.distance
                """,
                (blob, top_k),
            ).fetchall()
        except Exception as e:
            # Empty vec table or extension not loaded → return empty list, not error.
            print(f"[retriever] KNN query failed: {e}")
            return []

        results: list[dict] = []
        for row in rows:
            topics_raw = row[7]
            try:
                topics = json.loads(topics_raw) if topics_raw else []
            except (TypeError, ValueError):
                topics = []
            results.append({
                "chunk_id": row[0],
                "source_org": row[1],
                "source_title": row[2],
                "chunk_title": row[3],
                "content": row[4],
                "region": row[5],
                "crop": row[6],
                "topics": topics,
                "distance": row[8],
            })
        return results
    finally:
        if owns_session:
            session.close()
