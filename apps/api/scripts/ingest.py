"""Builds or refreshes the search index from knowledge/corpus. The API also does this at startup;
this script is for doing it by hand and seeing the counts.

    uv run python scripts/ingest.py
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.db.migrate import run_migrations
from app.rag.corpus import load_corpus
from app.rag.index import sync_index


def main() -> int:
    corpus_dir = get_settings().knowledge_dir / "corpus"
    if not corpus_dir.exists():
        print(f"ERROR: corpus dir not found at {corpus_dir}", file=sys.stderr)
        return 1
    run_migrations()
    result = sync_index()
    print(f"Read {result.chunks} chunks from {corpus_dir}")
    print(f"Added {result.added}, removed {result.removed}, unchanged {result.chunks - result.added}")
    by_crop = Counter(c.frontmatter.get("crop") or "(none)" for c in load_corpus(corpus_dir))
    print("Chunks by crop: " + ", ".join(f"{crop} {n}" for crop, n in sorted(by_crop.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
