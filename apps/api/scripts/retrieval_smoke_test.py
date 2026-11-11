"""Prints the top retrieval hits for a query, using the same code path as /api/ask.

    uv run python scripts/retrieval_smoke_test.py "when do I spray cowpea?"

Exits non-zero when nothing comes back, so CI can use it after an offline ingest.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.retriever import retrieve_chunks


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print('usage: scripts/retrieval_smoke_test.py "your query"', file=sys.stderr)
        return 2
    hits = retrieve_chunks(" ".join(argv[1:]), top_k=6)
    for i, hit in enumerate(hits, 1):
        print(f"{i}. [{hit['crop']}] {hit['chunk_title']}  ({hit['source_org']}, d={hit['distance']:.3f})")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
