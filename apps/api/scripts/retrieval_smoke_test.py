"""Hand-testing tool for the RAG retrieval path.

Embeds a query with `all-MiniLM-L6-v2`, KNN-searches the sqlite-vec
virtual table `document_chunks_vec`, and prints the top-6 hits with
their metadata. Run from repo root:

    python3.11 scripts/retrieval_smoke_test.py "your query"
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "apps" / "api"

os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from sentence_transformers import SentenceTransformer  # noqa: E402

from app.db import models  # noqa: E402,F401
from app.db.session import SessionLocal, engine  # noqa: E402

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 6


def vec_to_blob(vec) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python3.11 scripts/retrieval_smoke_test.py \"your query\"", file=sys.stderr)
        return 2
    query = " ".join(argv[1:])

    model = SentenceTransformer(MODEL_NAME)
    q_emb = model.encode(query, normalize_embeddings=True).tolist()
    q_blob = vec_to_blob(q_emb)

    conn = engine.raw_connection()
    session = SessionLocal()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT chunk_id, distance FROM document_chunks_vec "
            "WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (q_blob, TOP_K),
        )
        hits = cur.fetchall()
        if not hits:
            print("No results — is the vec table populated? Run scripts/ingest.py first.")
            return 1

        id_to_row = {}
        ids = [h[0] for h in hits]
        for row in session.query(models.DocumentChunk).filter(models.DocumentChunk.id.in_(ids)).all():
            id_to_row[row.id] = row

        print(f"Query: {query}\n")
        for rank, (chunk_id, distance) in enumerate(hits, start=1):
            row = id_to_row.get(chunk_id)
            if row is None:
                print(f"{rank}. [chunk_id={chunk_id} MISSING] distance={distance:.4f}")
                continue
            snippet = (row.content or "").replace("\n", " ").strip()[:150]
            print(
                f"{rank}. distance={distance:.4f} | org={row.source_org} | "
                f"title={row.chunk_title}"
            )
            print(f"     {snippet}")
    finally:
        session.close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
