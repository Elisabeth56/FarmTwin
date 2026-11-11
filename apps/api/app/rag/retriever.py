"""Production retrieval for FarmTwin.

- Embeds queries with the local fastembed model (app/rag/embedder.py).
- Runs KNN against the sqlite-vec virtual table `document_chunks_vec`.
- Joins to `document_chunks` for metadata and returns dicts.
"""

from __future__ import annotations

import json
import logging
import struct
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.rag.embedder import embed_query

logger = logging.getLogger(__name__)


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
        p
        for p in [
            crop_type or "",
            growth_stage or "",
            region or "",
            risk_str,
            user_question or "",
        ]
        if p
    )
    words = q.split()
    if len(words) > 40:
        words = words[:40]
    return " ".join(words)


def retrieve_chunks(
    query: str,
    top_k: int = 6,
    db_session: Session | None = None,
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
        blob = _vec_to_blob(embed_query(query))

        dbapi_conn = session.connection().connection
        cur = dbapi_conn.cursor()
        try:
            rows = cur.execute(
                """
                SELECT
                    dc.id, dc.source_org, dc.source_title, dc.chunk_title,
                    dc.content, dc.region, dc.crop, dc.topics,
                    v.distance, dc.source_id
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
            results.append(
                {
                    "chunk_id": row[0],
                    "source_org": row[1],
                    "source_title": row[2],
                    "chunk_title": row[3],
                    "content": row[4],
                    "region": row[5],
                    "crop": row[6],
                    "topics": topics,
                    "distance": row[8],
                    "source_id": row[9],
                }
            )
        return results
    finally:
        if owns_session:
            session.close()
