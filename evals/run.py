"""FarmTwin eval harness (ADR-024).

Runs the golden set in evals/cases.jsonl through the same retrieval path /api/ask uses, prints a
table, saves evals/results/<date>-retrieval.json, and compares with evals/results/baseline-retrieval.json.

    pnpm eval                      # from the repo root
    uv run python ../../evals/run.py --save-baseline   # from apps/api, after an accepted change

Needs an ingested index (apps/api/scripts/ingest.py) and the embedder on disk.
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

EVALS = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS.parent / "apps" / "api"))

from app.config import get_settings  # noqa: E402
from app.rag.retriever import build_query, retrieve  # noqa: E402

TOP_K = 6
BASELINE = EVALS / "results" / "baseline-retrieval.json"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in (EVALS / "cases.jsonl").read_text().splitlines() if line]


def run_case(case: dict) -> dict:
    query = build_query(" ".join(case["crops"]), case["stage"] or "", "", [], case["question"])
    start = time.perf_counter()
    result = retrieve(query, case["crops"] or None, top_k=TOP_K)
    hits = result.chunks
    latency_ms = (time.perf_counter() - start) * 1000

    sources = [h["source_id"] for h in hits]
    titles = [h["chunk_title"] for h in hits]
    expected = set(case["expected_sources"])
    first = next((i for i, s in enumerate(sources, 1) if s in expected), None)
    # chunk-level match is the stricter signal: several crops have only one or two source documents
    wanted = set(case["expected_chunks"])
    first_chunk = next((i for i, t in enumerate(titles, 1) if t in wanted), None)
    return {
        "id": case["id"],
        "answerable": case["answerable"],
        "tags": case["tags"],
        "crops": case["crops"],
        "retrieved": sources,
        "best_distance": result.best_distance,
        "refused": result.refused,
        "hit": first is not None,
        "recall": len(expected & set(sources)) / len(expected) if expected else None,
        "rr": 1 / first if first else 0.0,
        "chunk_rank": first_chunk,
        "chunk_rr": 1 / first_chunk if first_chunk else 0.0,
        "latency_ms": round(latency_ms, 1),
    }


def summarize(rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    latencies = sorted(r["latency_ms"] for r in rows)

    def mean(xs):
        return round(statistics.fmean(xs), 3) if xs else None

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in answerable:
        for key in [*r["crops"], *r["tags"]]:
            groups[key].append(r)

    return {
        "cases": len(rows),
        f"hit@{TOP_K}": mean([r["hit"] for r in answerable]),
        f"recall@{TOP_K}": mean([r["recall"] for r in answerable]),
        "mrr": mean([r["rr"] for r in answerable]),
        "chunk_hit@1": mean([r["chunk_rank"] == 1 for r in answerable]),
        f"chunk_hit@{TOP_K}": mean([r["chunk_rank"] is not None for r in answerable]),
        "chunk_mrr": mean([r["chunk_rr"] for r in answerable]),
        "refused_unanswerable": mean([r["refused"] for r in unanswerable]),
        "refused_answerable": mean([r["refused"] for r in answerable]),
        # the relevance cutoff (settings.retrieval_max_distance) sits between these two
        "best_distance_answerable": mean(
            [r["best_distance"] for r in answerable if r["best_distance"] is not None]
        ),
        "best_distance_unanswerable": mean(
            [r["best_distance"] for r in unanswerable if r["best_distance"] is not None]
        ),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": latencies[max(0, round(len(latencies) * 0.95) - 1)],
        "by_group": {
            k: {
                "n": len(v),
                "hit": mean([r["hit"] for r in v]),
                "chunk_mrr": mean([r["chunk_rr"] for r in v]),
            }
            for k, v in sorted(groups.items())
        },
    }


def print_report(summary: dict, rows: list[dict], baseline: dict | None) -> None:
    print(f"\n{'metric':<30}{'now':>10}{'baseline':>10}")
    for key, value in summary.items():
        if key == "by_group":
            continue
        before = (baseline or {}).get(key)
        print(f"{key:<30}{value!s:>10}{before!s:>10}")

    print(f"\n{'group':<16}{'n':>4}{'hit':>8}{'chunk_mrr':>11}")
    for name, g in summary["by_group"].items():
        print(f"{name:<16}{g['n']:>4}{g['hit']:>8}{g['chunk_mrr']:>11}")

    print("\nper case (best distance, rank of the expected chunk):")
    for r in sorted(rows, key=lambda r: r["best_distance"] or 0):
        rank = r["chunk_rank"] if r["answerable"] else "-"
        print(f"  {r['best_distance']:.3f}  {rank!s:>4}  {r['id']}")


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-baseline", action="store_true", help="also overwrite the baseline")
    args = parser.parse_args()

    rows = [run_case(c) for c in load_cases()]
    summary = summarize(rows)
    baseline = json.loads(BASELINE.read_text())["summary"] if BASELINE.exists() else None
    print_report(summary, rows, baseline)

    result = {
        "date": date.today().isoformat(),
        "commit": git_sha(),
        "embedder": get_settings().embedder_model,
        "max_distance": get_settings().retrieval_max_distance,
        "top_k": TOP_K,
        "summary": summary,
        "cases": rows,
    }
    out = EVALS / "results" / f"{date.today().isoformat()}-retrieval.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nsaved {out.relative_to(EVALS.parent)}")
    if args.save_baseline:
        BASELINE.write_text(json.dumps(result, indent=2) + "\n")
        print(f"saved {BASELINE.relative_to(EVALS.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
