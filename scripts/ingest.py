"""FarmTwin corpus ingestion.

Full-rebuild ingester: wipes `document_chunks` and its sqlite-vec sibling,
then walks `knowledge/corpus/*.md`, parses YAML-frontmatter chunks, embeds
each chunk with `all-MiniLM-L6-v2`, and stores rows + 384-d vectors.

Run from repo root:

    python3.11 scripts/ingest.py
"""

from __future__ import annotations

import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
CORPUS_DIR = REPO_ROOT / "knowledge" / "corpus"

# The backend's SQLAlchemy URL is `sqlite:///./farmtwin.db` (relative to CWD).
# chdir before importing so we hit backend/farmtwin.db, matching uvicorn's CWD.
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

import yaml  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.db import models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402

MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384


def parse_corpus_file(path: Path) -> list[dict]:
    """Split a corpus file into (frontmatter, content) chunks.

    Files are a sequence of `---`-separated blocks; a frontmatter block
    (parseable as YAML with expected keys) is paired with the block that
    follows it as the content.
    """
    text = path.read_text(encoding="utf-8")
    raw_blocks = [b.strip() for b in text.split("---")]
    blocks = [b for b in raw_blocks if b]

    chunks: list[dict] = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        fm = None
        if "source_id" in block or "source_title" in block:
            try:
                candidate = yaml.safe_load(block)
                if isinstance(candidate, dict) and (
                    "source_id" in candidate or "source_title" in candidate
                ):
                    fm = candidate
            except yaml.YAMLError:
                fm = None
        if fm is not None and i + 1 < len(blocks):
            content = blocks[i + 1].strip()
            chunk_title = None
            body_lines = content.splitlines()
            if body_lines and body_lines[0].startswith("# Chunk:"):
                chunk_title = body_lines[0].removeprefix("# Chunk:").strip()
                content = "\n".join(body_lines[1:]).strip()
            chunks.append({"frontmatter": fm, "chunk_title": chunk_title, "content": content})
            i += 2
        else:
            i += 1
    return chunks


def vec_to_blob(vec) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def main() -> int:
    if not CORPUS_DIR.exists():
        print(f"ERROR: corpus dir not found at {CORPUS_DIR}", file=sys.stderr)
        return 1

    Base.metadata.create_all(bind=engine)

    print(f"Loading sentence-transformers model: {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    if dim != EMBED_DIM:
        print(f"ERROR: expected embedding dim {EMBED_DIM}, got {dim}", file=sys.stderr)
        return 1
    print(f"Model loaded, embedding dim = {dim}")

    files = sorted(CORPUS_DIR.glob("*.md"))
    print(f"Found {len(files)} corpus files")

    session = SessionLocal()
    # Share the session's underlying DBAPI connection with our raw vec-table
    # writes; two separate sqlite connections on the same file would deadlock.
    dbapi_conn = session.connection().connection
    try:
        cur = dbapi_conn.cursor()
        cur.execute("DROP TABLE IF EXISTS document_chunks_vec")
        cur.execute(
            "CREATE VIRTUAL TABLE document_chunks_vec USING vec0("
            "chunk_id INTEGER PRIMARY KEY, "
            f"embedding FLOAT[{EMBED_DIM}])"
        )
        print("Recreated virtual table document_chunks_vec")

        session.query(models.DocumentChunk).delete()
        session.commit()
        print("Cleared document_chunks")

        total_chunks = 0
        files_ok = 0
        file_errors: list[tuple[str, str]] = []
        chunk_errors: list[tuple[str, int, str]] = []
        org_counter: Counter = Counter()
        crop_counter: Counter = Counter()

        for fp in files:
            try:
                parsed = parse_corpus_file(fp)
            except Exception as e:  # noqa: BLE001
                file_errors.append((fp.name, str(e)))
                print(f"  ERROR parsing {fp.name}: {e}")
                continue

            if not parsed:
                print(f"  WARN {fp.name}: no chunks parsed")
                continue

            print(f"  {fp.name}: {len(parsed)} chunks")
            files_ok += 1

            for idx, ch in enumerate(parsed):
                try:
                    fm = ch["frontmatter"] or {}
                    content = ch["content"]
                    topics = fm.get("topics") or []
                    if not isinstance(topics, list):
                        topics = [str(topics)]

                    row = models.DocumentChunk(
                        source_id=fm.get("source_id"),
                        source_title=fm.get("source_title"),
                        source_org=fm.get("source_org"),
                        source_url=fm.get("source_url"),
                        source_note=fm.get("source_note"),
                        region=fm.get("region"),
                        crop=fm.get("crop"),
                        topics=json.dumps(topics),
                        chunk_title=ch.get("chunk_title"),
                        token_count=len(content.split()),
                        content=content,
                    )
                    session.add(row)
                    session.flush()

                    emb = model.encode(content, normalize_embeddings=True).tolist()
                    cur.execute(
                        "INSERT INTO document_chunks_vec(chunk_id, embedding) VALUES (?, ?)",
                        (row.id, vec_to_blob(emb)),
                    )
                    total_chunks += 1
                    org_counter[fm.get("source_org") or "(none)"] += 1
                    crop_counter[fm.get("crop") or "(none)"] += 1
                except Exception as e:  # noqa: BLE001
                    chunk_errors.append((fp.name, idx, str(e)))
                    print(f"    ERROR {fp.name} chunk {idx}: {e}")

        session.commit()
    finally:
        session.close()

    print("\n=== Ingestion summary ===")
    print(f"Files processed OK : {files_ok}/{len(files)}")
    print(f"Total chunks       : {total_chunks}")
    print("\nBy source_org:")
    for org, n in sorted(org_counter.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:>3}  {org}")
    print("\nBy crop:")
    for crop, n in sorted(crop_counter.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:>3}  {crop}")
    if file_errors:
        print("\nFile errors:")
        for name, err in file_errors:
            print(f"  {name}: {err}")
    if chunk_errors:
        print("\nChunk errors:")
        for name, idx, err in chunk_errors:
            print(f"  {name}[{idx}]: {err}")
    if not file_errors and not chunk_errors:
        print("\nNo errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
