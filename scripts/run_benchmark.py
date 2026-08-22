"""Day 6 FarmTwin benchmark harness.

Runs the 10 gold prompts against a running llama-server and captures
timing / memory / structural quality metrics per prompt.

Preconditions:
  - llama-server is ALREADY RUNNING at http://127.0.0.1:8080 with the
    candidate GGUF loaded (this script does NOT start or stop it —
    memory hygiene is the user's job on an 8GB Intel Mac).
  - backend/farmtwin.db is populated (ingest.py already run) so the
    retriever can pull chunks.
  - Run from the repo root:
      python scripts/run_benchmark.py --model-name qwen \
          --output evaluation/bench_results/qwen.json

The --model-name is a label for the output only. Which GGUF is actually
evaluated is controlled by how the user launched llama-server.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

# Import backend engines from the backend/ package root. The retriever expects
# to open farmtwin.db by its relative path, so we also chdir there.
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app.engines.context_assembler import assemble_prompt  # noqa: E402
from app.engines.crop_calendar import compute_growth_stage  # noqa: E402
from app.engines.risk_rules import evaluate_risks  # noqa: E402
from app.llm import client as llm_client  # noqa: E402
from app.rag.retriever import build_query, retrieve_chunks  # noqa: E402


GOLD_PATH = REPO_ROOT / "evaluation" / "gold_prompts.json"
LLAMA_CPP_DIR = Path.home() / "dev" / "tools" / "llama.cpp"

_LEADING_NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+")


def _extract_number(text: str) -> Optional[float]:
    if not text:
        return None
    m = _LEADING_NUMBER_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _to_engine_observations(raw_obs: list[dict]) -> list[dict]:
    """Translate gold-fixture observation shape to what risk_rules expects.

    Fixture uses {date, type, value}. The engine uses {obs_type,
    value_numeric, value_text, observed_at, unit}.
    """
    engine_obs: list[dict] = []
    for o in raw_obs or []:
        otype = (o.get("type") or "").lower().strip()
        val = o.get("value") or ""
        entry: dict[str, Any] = {
            "obs_type": otype,
            "observed_at": o.get("date"),
            "value_text": val,
        }
        if otype == "rainfall":
            entry["value_numeric"] = _extract_number(val)
            entry["unit"] = "mm"
        elif otype == "humidity":
            entry["value_numeric"] = _extract_number(val)
            entry["unit"] = "%"
        engine_obs.append(entry)
    return engine_obs


def _display_facts(fixture: dict, stage_info: dict) -> dict:
    """Build the farm_facts dict shown to the model (matches ADR-conformant shape)."""
    return {
        "farm_name": fixture.get("farm_name"),
        "region": fixture.get("region"),
        "area_hectares": fixture.get("area_hectares"),
        "field_name": fixture.get("field_name"),
        "soil_type": fixture.get("soil_type"),
        "crop": fixture.get("crop"),
        "variety": fixture.get("variety"),
        "planting_date": fixture.get("planting_date"),
        "current_stage": stage_info["stage"],
        "days_since_planting": stage_info["days_since_planting"],
        "recent_observations": fixture.get("recent_observations") or [],
        "latest_weather": fixture.get("latest_weather"),
    }


def _peak_rss_mb() -> Optional[int]:
    """Read llama-server RSS in MB via ps. Returns None if not found."""
    try:
        pgrep = subprocess.run(
            ["pgrep", "-f", "llama-server"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        pids = [p for p in pgrep.stdout.strip().splitlines() if p.strip()]
        if not pids:
            return None
        pid = pids[0].strip()
        ps = subprocess.run(
            ["ps", "-p", pid, "-o", "rss="],
            capture_output=True,
            text=True,
            timeout=3,
        )
        raw = ps.stdout.strip()
        if not raw:
            return None
        rss_kb = int(raw.split()[0])
        return rss_kb // 1024
    except Exception:
        return None


def _llama_cpp_tag() -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(LLAMA_CPP_DIR), "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        tag = r.stdout.strip()
        return tag or "unknown"
    except Exception:
        return "unknown"


def _extract_json_recs(content: str) -> tuple[bool, list]:
    parsed = llm_client.extract_json_block(content)
    if not parsed:
        return False, []
    recs = parsed.get("recommendations")
    if not isinstance(recs, list):
        return True, []
    return True, recs


_CITE_RE = re.compile(r"\[K\d+\]")


def _cited_chunks(content: str) -> list[str]:
    seen: list[str] = []
    for m in _CITE_RE.findall(content or ""):
        if m not in seen:
            seen.append(m)
    return seen


def _warmup() -> None:
    """One tiny throwaway call so the first real prompt isn't cold."""
    print("[warmup] sending discardable prompt...")
    try:
        llm_client.generate(
            prompt="Hello.",
            n_predict=8,
            temperature=0.1,
        )
        print("[warmup] done")
    except Exception as e:
        print(f"[warmup] failed (continuing anyway): {e}")


def _run_one(item: dict) -> dict:
    fixture = item["farm_fixture"]
    question = item["question"]

    planting = datetime.fromisoformat(fixture["planting_date"]).date()
    stage_info = compute_growth_stage(fixture["crop"], planting)

    engine_obs = _to_engine_observations(fixture.get("recent_observations"))
    risk_flags = evaluate_risks(
        crop_type=fixture["crop"],
        growth_stage=stage_info["stage"],
        recent_observations=engine_obs,
        latest_weather=fixture.get("latest_weather"),
    )

    retrieval_query = build_query(
        crop_type=fixture["crop"],
        growth_stage=stage_info["stage"],
        region=fixture.get("region") or "",
        risk_flags=risk_flags,
        user_question=question,
    )
    chunks = retrieve_chunks(retrieval_query, top_k=6)

    display_facts = _display_facts(fixture, stage_info)
    prompt = assemble_prompt(
        farm_facts=display_facts,
        risk_flags=risk_flags,
        chunks=chunks,
        user_question=question,
    )

    t0 = time.perf_counter()
    resp = llm_client.generate(
        prompt=prompt,
        n_predict=600,
        temperature=0.3,
    )
    wall = time.perf_counter() - t0

    content = llm_client.extract_content(resp)
    timings = resp.get("timings") or {}

    json_ok, recs = _extract_json_recs(content)
    cited = _cited_chunks(content)

    return {
        "id": item["id"],
        "question": question,
        "farm_fixture_id": fixture.get("farm_name"),
        "computed_stage": stage_info["stage"],
        "days_since_planting": stage_info["days_since_planting"],
        "risk_flags_fired": [f.name for f in risk_flags],
        "retrieved_chunk_ids": [c.get("chunk_id") for c in chunks],
        "prompt_chars": len(prompt),
        "prompt_tokens": timings.get("prompt_n"),
        "gen_tokens": timings.get("predicted_n"),
        "prompt_eval_tok_s": timings.get("prompt_per_second"),
        "gen_tok_s": timings.get("predicted_per_second"),
        "prompt_ms": timings.get("prompt_ms"),
        "predicted_ms": timings.get("predicted_ms"),
        "wall_clock_s": round(wall, 2),
        "response_full": content,
        "response_narrative_preview": content[:500],
        "recommendations_parsed": recs,
        "cited_chunks": cited,
        "json_parseable": json_ok,
    }


def _aggregate(rows: list[dict], peak_rss_mb: Optional[int], total_time_s: float) -> dict:
    def _mean(key: str) -> Optional[float]:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 2)

    return {
        "n_prompts": len(rows),
        "mean_prompt_tokens": _mean("prompt_tokens"),
        "mean_gen_tokens": _mean("gen_tokens"),
        "mean_prompt_eval_tok_s": _mean("prompt_eval_tok_s"),
        "mean_gen_tok_s": _mean("gen_tok_s"),
        "mean_wall_clock_s": _mean("wall_clock_s"),
        "peak_rss_mb": peak_rss_mb,
        "total_time_min": round(total_time_s / 60.0, 2),
        "json_parse_rate": round(
            sum(1 for r in rows if r.get("json_parseable")) / max(len(rows), 1), 3
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run FarmTwin gold-prompt benchmark.")
    ap.add_argument("--model-name", required=True, help="Label for this run (qwen, llama, ...)")
    ap.add_argument("--output", required=True, help="Output JSON path")
    args = ap.parse_args()

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(REPO_ROOT / "evaluation" / "gold_prompts.json") as f:
        gold = json.load(f)

    if not llm_client.health_check():
        print("ERROR: llama-server /health did not return 200 at "
              f"{llm_client.LLAMA_HEALTH_URL}. Start it before running.")
        return 2

    print(f"Loaded {len(gold)} gold prompts. Model label: {args.model_name}")
    _warmup()

    peak_rss = 0
    per_prompt: list[dict] = []
    bench_t0 = time.perf_counter()

    for i, item in enumerate(gold, 1):
        row = _run_one(item)
        per_prompt.append(row)

        rss = _peak_rss_mb()
        if rss is not None and rss > peak_rss:
            peak_rss = rss

        preview = (row["response_narrative_preview"] or "").replace("\n", " ")[:80]
        p_tps = row.get("prompt_eval_tok_s") or 0.0
        g_tps = row.get("gen_tok_s") or 0.0
        print(
            f"[{i:2d}/{len(gold)}] {row['id']}: {preview}... "
            f"{row['wall_clock_s']:.1f}s "
            f"(prompt {p_tps:.1f} t/s, gen {g_tps:.1f} t/s, "
            f"rss {rss}MB)"
        )

    total_time = time.perf_counter() - bench_t0

    output = {
        "model_name": args.model_name,
        "run_date": date.today().isoformat(),
        "environment": {
            "os": "macOS",
            "cpu": "Intel Core (2014 MacBook Pro)",
            "ram_gb": 8,
            "llama_cpp_tag": _llama_cpp_tag(),
            "n_ctx": 4096,
            "threads": 4,
            "load_mode": "mlock",
        },
        "aggregate": _aggregate(per_prompt, peak_rss if peak_rss else None, total_time),
        "per_prompt": per_prompt,
    }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nWrote {out_path}")
    print(f"Total wall clock: {total_time / 60.0:.1f} min")
    print(f"Peak llama-server RSS observed: {peak_rss} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
