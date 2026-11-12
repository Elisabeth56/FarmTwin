"""Answer eval (ADR-024): asks every golden-set question through the real /api/ask with the real
model, checks the answers, optionally grades them with an LLM judge, and records speed and memory.

Runs in a scratch data folder, so your own farms are untouched. Needs the embedder and a model:

    FARMTWIN_LLAMA_SERVER_BIN=/path/to/llama-server \
    FARMTWIN_LLM_MODEL_PATH=/path/to/qwen2.5-3b-instruct-q4_k_m.gguf \
    GROQ_API_KEY=...            # optional: adds the judge scores
    pnpm eval:answers           # from the repo root; add -- --sample 10 for a quick run

Saves evals/results/<date>-answers.json and prints a table.
"""

import json
import os
import statistics
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path

EVALS = Path(__file__).resolve().parent
API = EVALS.parent / "apps" / "api"
sys.path.insert(0, str(API))
sys.path.insert(0, str(API / "scripts"))

from platformdirs import user_data_dir  # noqa: E402

# a scratch data folder, set before the app reads its settings; the embedder is shared with the
# real app's folder so it's only downloaded once
os.environ.setdefault("FARMTWIN_EMBEDDER_DIR", str(Path(user_data_dir("FarmTwin")) / "models" / "embedder"))
os.environ["FARMTWIN_DATA_DIR"] = tempfile.mkdtemp(prefix="farmtwin-eval-")

import httpx  # noqa: E402
import ingest  # noqa: E402
import psutil  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.ai import prompts  # noqa: E402
from app.ai.server import supervisor  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.engines.rules import load_crops  # noqa: E402
from app.main import app  # noqa: E402
from app.rag.embedder import get_model  # noqa: E402

JUDGE_URL = "https://api.groq.com/openai/v1/chat/completions"
JUDGE_MODEL = "llama-3.3-70b-versatile"
JUDGE_PROMPT = (EVALS / "judge.md").read_text()


def main() -> int:
    get_model(local_files_only=False)  # downloads the embedder the first time only
    if ingest.main() != 0:
        return 1
    cases = [json.loads(line) for line in (EVALS / "cases.jsonl").read_text().splitlines() if line]
    # --sample N runs N evenly spread cases: a full run is about an hour on the 2014 MacBook
    if "--sample" in sys.argv:
        n = int(sys.argv[sys.argv.index("--sample") + 1])
        cases = [cases[round(i * (len(cases) - 1) / max(n - 1, 1))] for i in range(n)]
    judge_key = os.environ.get("GROQ_API_KEY")
    if not judge_key:
        print("GROQ_API_KEY not set: skipping the judge, running the rule checks only")

    with TestClient(app) as client:
        _wait_for_model(client)
        memory = _MemoryWatch()
        rows = []
        for i, case in enumerate(cases, 1):
            row = _ask(client, case)
            if judge_key and row["kind"] == "answer" and row["status"] == 200:
                row["judge"] = _judge(judge_key, case, row)
            rows.append(row)
            print(f"[{i}/{len(cases)}] {case['id']}: {row['kind']} {row['total_ms']}ms {_flag(row)}")
        peak = memory.stop()

    summary = _summarize(rows, peak)
    _print(summary)
    result = {
        "date": date.today().isoformat(),
        "machine": _machine(),
        "model": get_settings().llm_model,
        "model_file": str(get_settings().llm_model_path),
        "prompt_version": prompts.ASK_VERSION,
        "judge_model": JUDGE_MODEL if judge_key else None,
        "summary": summary,
        "cases": rows,
    }
    out = EVALS / "results" / f"{date.today().isoformat()}-answers.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(f"\nsaved {out.relative_to(EVALS.parent)}")
    return 0


def _wait_for_model(client: TestClient) -> None:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        state = client.get("/api/model/status").json()["state"]
        if state == "ready":
            return
        if state in ("stopped", "not_set_up"):
            raise SystemExit(f"model is {state}: set FARMTWIN_LLAMA_SERVER_BIN and FARMTWIN_LLM_MODEL_PATH")
        time.sleep(1)
    raise SystemExit("model didn't become ready within 3 minutes")


def _ask(client: TestClient, case: dict) -> dict:
    """Builds a one-field farm matching the case, then asks its question."""
    farm = client.post("/api/farms", json={"name": f"eval {case['id']}", "region": "Kaduna"}).json()
    field = client.post("/api/fields", json={"farm_id": farm["id"], "name": "Main field"}).json()
    for crop in case["crops"] or ["maize"]:
        client.post(
            "/api/plantings",
            json={
                "field_id": field["id"],
                "crop_type": crop,
                "planting_date": _planted_for(crop, case["stage"]).isoformat(),
                "status": "active",
            },
        )
    started = time.perf_counter()
    res = client.post("/api/ask", json={"farm_id": farm["id"], "question": case["question"]})
    total_ms = round((time.perf_counter() - started) * 1000)
    body = res.json()
    if res.status_code != 200:
        return {
            "id": case["id"],
            "status": res.status_code,
            "kind": "error",
            "error": body,
            "total_ms": total_ms,
        }

    cited = [c["source_id"] for c in body["cited_chunks"]]
    return {
        "id": case["id"],
        "status": 200,
        "answerable": case["answerable"],
        "tags": case["tags"],
        "kind": body["kind"],
        "narrative": body["narrative"],
        "recommendations": body["recommendations"],
        "cited_sources": cited,
        "cited_chunks": [c["chunk_title"] for c in body["cited_chunks"]],
        "context": [c["content"] for c in body["cited_chunks"]],
        "checks": {
            "refused_correctly": body["kind"] != "answer" if not case["answerable"] else None,
            "answered": body["kind"] == "answer" if case["answerable"] else None,
            "has_cards": bool(body["recommendations"]) if body["kind"] == "answer" else None,
            "cites_a_source": bool(cited) if body["kind"] == "answer" else None,
            "cites_expected_source": bool(set(cited) & set(case["expected_sources"]))
            if case["answerable"]
            else None,
        },
        # prompt processing time is what the farmer waits before the first word appears
        "ttft_ms": body["timing_ms"].get("prompt_ms"),
        "total_ms": total_ms,
    }


def _planted_for(crop: str, stage: str | None) -> date:
    """A planting date that puts the crop a few days into the case's stage."""
    spec = load_crops()[0].get(crop)
    day = 30
    if spec and stage:
        match = next((s for s in spec.stages if s.id == stage), None)
        if match:
            day = match.from_day + 5
    return date.today() - timedelta(days=day)


def _judge(key: str, case: dict, row: dict) -> dict:
    """Scores faithfulness to the cited passages and correctness against the key facts, 1 to 5."""
    prompt = JUDGE_PROMPT.format(
        question=case["question"],
        key_facts="\n".join(f"- {f}" for f in case["key_facts"]),
        passages="\n\n".join(row["context"]) or "(no passages cited)",
        answer=row["narrative"] + "\n\n" + json.dumps(row["recommendations"], indent=1),
    )
    error = "rate limited"
    for attempt in range(3):
        try:
            res = httpx.post(
                JUDGE_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": JUDGE_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
                timeout=60,
            )
            if res.status_code == 429:  # free tier rate limit: wait and retry
                time.sleep(10 * (attempt + 1))
                continue
            res.raise_for_status()
            verdict = json.loads(res.json()["choices"][0]["message"]["content"])
            return {k: verdict.get(k) for k in ("faithfulness", "correctness", "notes")}
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            error = str(exc)
    return {"error": error}


class _MemoryWatch:
    """Samples the resident memory of the API and llama-server every half second."""

    def __init__(self) -> None:
        self.peak = {"api_mb": 0.0, "llama_mb": 0.0}
        self._stop = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        me = psutil.Process()
        while not self._stop.is_set():
            self.peak["api_mb"] = max(self.peak["api_mb"], me.memory_info().rss / 2**20)
            proc = supervisor._proc
            if proc and proc.poll() is None:
                try:
                    rss = psutil.Process(proc.pid).memory_info().rss / 2**20
                    self.peak["llama_mb"] = max(self.peak["llama_mb"], rss)
                except psutil.Error:
                    pass
            time.sleep(0.5)

    def stop(self) -> dict:
        self._stop.set()
        return {k: round(v) for k, v in self.peak.items()}


def _summarize(rows: list[dict], peak: dict) -> dict:
    def rate(key: str):
        values = [r["checks"][key] for r in rows if r.get("checks") and r["checks"][key] is not None]
        return round(sum(values) / len(values), 3) if values else None

    def score(key: str):
        values = [r["judge"][key] for r in rows if isinstance(r.get("judge", {}).get(key), int | float)]
        return round(statistics.fmean(values), 2) if values else None

    ttft = sorted(r["ttft_ms"] for r in rows if r.get("ttft_ms"))
    total = sorted(r["total_ms"] for r in rows if r.get("kind") == "answer")
    return {
        "cases": len(rows),
        "errors": sum(r["status"] != 200 for r in rows),
        "answered": rate("answered"),
        "refused_correctly": rate("refused_correctly"),
        "has_cards": rate("has_cards"),
        "cites_a_source": rate("cites_a_source"),
        "cites_expected_source": rate("cites_expected_source"),
        "judge_faithfulness": score("faithfulness"),
        "judge_correctness": score("correctness"),
        "ttft_p50_ms": _pct(ttft, 0.5),
        "ttft_p95_ms": _pct(ttft, 0.95),
        "answer_p50_ms": _pct(total, 0.5),
        "answer_p95_ms": _pct(total, 0.95),
        "peak_api_mb": peak["api_mb"],
        "peak_llama_mb": peak["llama_mb"],
        "peak_total_mb": peak["api_mb"] + peak["llama_mb"],
    }


def _pct(values: list, q: float):
    return values[max(0, round(len(values) * q) - 1)] if values else None


def _print(summary: dict) -> None:
    print()
    for key, value in summary.items():
        print(f"{key:<26}{value!s:>10}")


def _flag(row: dict) -> str:
    failed = [k for k, v in (row.get("checks") or {}).items() if v is False]
    return f"FAILED {', '.join(failed)}" if failed else ""


def _machine() -> dict:
    import platform

    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "memory_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "cpus": psutil.cpu_count(),
    }


if __name__ == "__main__":
    raise SystemExit(main())
