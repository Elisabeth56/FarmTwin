"""Day 6 FarmTwin manual grader.

Reads a benchmark output JSON (produced by run_benchmark.py) and walks
you through the 10 responses interactively. For each one you score five
0-5 rubric dimensions:

  1. farm_grounding      — did it use the farm facts?
  2. retrieval_grounding — do cited chunks actually support claims?
  3. agronomic_factuality — anything obviously wrong vs. corpus?
  4. actionability       — are recommendations useful and specific?
  5. structure           — valid JSON, WHAT/WHY/WHEN/RISK all present?

Scores are written back into the same JSON under per_prompt[i].grade.
State is saved after every prompt so --resume picks up where you left off.

Usage:
  python scripts/grade_benchmark.py --file evaluation/bench_results/qwen.json
  python scripts/grade_benchmark.py --file evaluation/bench_results/qwen.json --resume
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DIMENSIONS = [
    ("farm_grounding", "1) Farm-context grounding — did it use the farm facts?"),
    ("retrieval_grounding", "2) Retrieval grounding — do cited chunks actually support claims?"),
    ("agronomic_factuality", "3) Agronomic factuality — anything obviously wrong vs. corpus?"),
    ("actionability", "4) Actionability — are recommendations useful and specific?"),
    ("structure", "5) Structure conformance — valid JSON, WHAT/WHY/WHEN/RISK present?"),
]


def _load_gold() -> dict[str, dict]:
    with open(REPO_ROOT / "evaluation" / "gold_prompts.json") as f:
        return {item["id"]: item for item in json.load(f)}


def _prompt_score(label: str) -> int:
    while True:
        raw = input(f"  {label} [0-5]: ").strip()
        if raw == "":
            print("  (must enter a number 0-5)")
            continue
        try:
            v = int(raw)
        except ValueError:
            print("  (not a number, try again)")
            continue
        if 0 <= v <= 5:
            return v
        print("  (out of range 0-5)")


def _print_prompt(row: dict, gold: dict) -> None:
    print("\n" + "=" * 78)
    print(f"PROMPT {row['id']}")
    print("=" * 78)
    print(f"\nQuestion:\n  {row['question']}")

    fixture = gold.get("farm_fixture", {})
    print("\nFarm fixture:")
    for k in ("farm_name", "region", "crop", "variety", "planting_date"):
        if k in fixture:
            print(f"  {k}: {fixture[k]}")
    print(f"  computed_stage: {row.get('computed_stage')} "
          f"(day {row.get('days_since_planting')})")
    obs = fixture.get("recent_observations") or []
    if obs:
        print("  recent_observations:")
        for o in obs:
            print(f"    - {o.get('date')} {o.get('type')}: {o.get('value')}")
    lw = fixture.get("latest_weather")
    if lw:
        print(f"  latest_weather: {lw}")
    ff = row.get("risk_flags_fired") or []
    if ff:
        print(f"  risk_flags_fired: {', '.join(ff)}")

    print("\nRubric:")
    rubric = gold.get("rubric", {})
    for k, v in rubric.items():
        print(f"  {k}: {v}")

    print("\nRetrieved chunk ids:", row.get("retrieved_chunk_ids"))
    print("Cited chunks in response:", row.get("cited_chunks"))
    print(f"JSON parseable: {row.get('json_parseable')}")

    print("\n----- FULL RESPONSE -----")
    print(row.get("response_full") or "(empty)")
    print("----- END RESPONSE -----\n")


def _save(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(path)


def _print_aggregate(data: dict) -> None:
    graded = [r for r in data["per_prompt"] if r.get("grade")]
    if not graded:
        print("\nNo graded rows yet.")
        return
    print("\n" + "=" * 78)
    print(f"AGGREGATE SCORES ({len(graded)} graded)")
    print("=" * 78)
    per_dim_totals: dict[str, int] = {k: 0 for k, _ in DIMENSIONS}
    total_points = 0
    for r in graded:
        g = r["grade"]
        for k, _ in DIMENSIONS:
            per_dim_totals[k] += int(g.get(k, 0))
            total_points += int(g.get(k, 0))
    for k, label in DIMENSIONS:
        mean = per_dim_totals[k] / len(graded)
        print(f"  {label}\n    mean: {mean:.2f} / 5.00   total: {per_dim_totals[k]}")
    max_points = len(graded) * len(DIMENSIONS) * 5
    print(f"\n  Total points: {total_points} / {max_points}")
    # Scale to 0-100. Spec: "sum of all 50 possible points × 2 (to get 0-100 scale)"
    # (i.e. 25 possible points per prompt × 10 prompts = 250 max; ÷ 250 × 100.)
    scaled = (total_points / max_points) * 100.0 if max_points else 0.0
    print(f"  Accuracy score (0-100 scale): {scaled:.1f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Manually grade a benchmark run.")
    ap.add_argument("--file", required=True, help="Path to bench results JSON")
    ap.add_argument("--resume", action="store_true",
                    help="Skip prompts that already have a grade")
    ap.add_argument("--only", default=None,
                    help="Grade only this prompt id (e.g. g03)")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        print(f"ERROR: {path} not found")
        return 2

    with open(path) as f:
        data = json.load(f)

    gold_by_id = _load_gold()
    rows = data.get("per_prompt") or []
    if not rows:
        print("ERROR: no per_prompt entries in file")
        return 2

    print(f"Loaded {len(rows)} responses from {path.name} "
          f"(model: {data.get('model_name')})")

    graded_count = 0
    for row in rows:
        if args.only and row["id"] != args.only:
            continue
        if args.resume and row.get("grade"):
            print(f"[skip] {row['id']} already graded")
            continue

        gold = gold_by_id.get(row["id"], {})
        _print_prompt(row, gold)

        print("Score each dimension 0-5. Ctrl-C to save-and-quit.")
        try:
            grade: dict[str, int | str] = {}
            for key, label in DIMENSIONS:
                grade[key] = _prompt_score(label)
            notes = input("  Optional notes (enter to skip): ").strip()
            if notes:
                grade["notes"] = notes
        except (KeyboardInterrupt, EOFError):
            print("\n[interrupted] saving progress and exiting")
            _save(path, data)
            _print_aggregate(data)
            return 0

        row["grade"] = grade
        graded_count += 1
        _save(path, data)
        print(f"  [saved] {row['id']} scored, total this session: {graded_count}")

    _print_aggregate(data)
    print(f"\nGrades saved to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
