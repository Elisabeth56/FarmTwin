"""Hybrid retrieval for FarmTwin (ADR-018).

Vector KNN (sqlite-vec) and keyword search (FTS5) each rank candidates for the farm's crops; the
two rankings are merged with reciprocal rank fusion. If even the closest vector match is further
than `retrieval_max_distance`, nothing is returned and /api/ask answers "not in my sources".
"""

from __future__ import annotations

import json
import logging
import re
import struct
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
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


CANDIDATES = 20
VEC_POOL = 60  # KNN runs before the crop filter, so it fetches extra to leave enough after it
RRF_K = 60

_COLUMNS = """
    dc.id, dc.source_id, dc.source_org, dc.source_title, dc.chunk_title,
    dc.content, dc.region, dc.crop, dc.topics
"""


@dataclass
class Retrieval:
    chunks: list[dict]
    best_distance: float | None

    @property
    def refused(self) -> bool:
        """True when the corpus has nothing close enough to the question."""
        return not self.chunks


def retrieve(
    query: str,
    crops: list[str] | None = None,
    top_k: int = 6,
    db_session: Session | None = None,
) -> Retrieval:
    """Returns up to top_k chunks for the query, limited to `crops` when given."""
    if not query or not query.strip():
        return Retrieval([], None)

    owns_session = db_session is None
    session = db_session or SessionLocal()
    # raw queries share the session's connection, which has sqlite-vec loaded
    cur = session.connection().connection.cursor()
    try:
        vec_rows = _vector_search(cur, query, crops)
        fts_rows = _keyword_search(cur, query, crops)
    finally:
        if owns_session:
            session.close()

    best = vec_rows[0]["distance"] if vec_rows else None
    if best is None or best > get_settings().retrieval_max_distance:
        return Retrieval([], best)

    scores: dict[int, float] = {}
    by_id: dict[int, dict] = {}
    for ranking in (vec_rows, fts_rows):
        for rank, row in enumerate(ranking, 1):
            scores[row["chunk_id"]] = scores.get(row["chunk_id"], 0.0) + 1 / (RRF_K + rank)
            by_id.setdefault(row["chunk_id"], row)
    ordered = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]
    return Retrieval([by_id[cid] for cid in ordered], best)


def retrieve_chunks(query: str, top_k: int = 6, db_session: Session | None = None) -> list[dict]:
    """Chunks only, across all crops; kept for the v1 benchmark script."""
    return retrieve(query, None, top_k, db_session).chunks


def _crop_filter(crops: list[str] | None) -> tuple[str, list[str]]:
    if not crops:
        return "", []
    return f" AND dc.crop IN ({','.join('?' * len(crops))})", list(crops)


def _vector_search(cur, query: str, crops: list[str] | None) -> list[dict]:
    clause, params = _crop_filter(crops)
    # outside the try: a missing embedder must surface as its own error, not as "nothing found"
    blob = _vec_to_blob(embed_query(query))
    try:
        rows = cur.execute(
            f"""
            SELECT {_COLUMNS}, v.distance
            FROM document_chunks_vec v
            JOIN document_chunks dc ON dc.id = v.chunk_id
            WHERE v.embedding MATCH ? AND k = ?{clause}
            ORDER BY v.distance
            LIMIT ?
            """,
            (blob, VEC_POOL, *params, CANDIDATES),
        ).fetchall()
    except Exception:
        # empty index or sqlite-vec not loaded: behave like "nothing found"
        logger.exception("vector search failed")
        return []
    return [_row(r, distance=r[9]) for r in rows]


def _keyword_search(cur, query: str, crops: list[str] | None) -> list[dict]:
    terms = _fts_terms(query)
    if not terms:
        return []
    clause, params = _crop_filter(crops)
    try:
        rows = cur.execute(
            f"""
            SELECT {_COLUMNS}
            FROM document_chunks_fts f
            JOIN document_chunks dc ON dc.id = f.rowid
            WHERE document_chunks_fts MATCH ?{clause}
            ORDER BY bm25(document_chunks_fts)
            LIMIT ?
            """,
            (terms, *params, CANDIDATES),
        ).fetchall()
    except Exception:
        logger.exception("keyword search failed")
        return []
    return [_row(r, distance=None) for r in rows]


def _fts_terms(query: str) -> str:
    """Turns free text into an FTS5 OR query; quoting each word keeps user text from being parsed as syntax."""
    words = dict.fromkeys(w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", query))
    return " OR ".join(f'"{w}"' for w in words)


def _row(r, distance: float | None) -> dict:
    try:
        topics = json.loads(r[8]) if r[8] else []
    except (TypeError, ValueError):
        topics = []
    return {
        "chunk_id": r[0],
        "source_id": r[1],
        "source_org": r[2],
        "source_title": r[3],
        "chunk_title": r[4],
        "content": r[5],
        "region": r[6],
        "crop": r[7],
        "topics": topics,
        "distance": distance,
    }
