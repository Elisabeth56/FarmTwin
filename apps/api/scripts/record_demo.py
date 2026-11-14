"""Records what the website demo shows: the sample farm as the real API returns it, and, with
--answers, the real model's streamed answers to the suggested questions.

    uv run python scripts/record_demo.py              # farm data only, no model needed
    uv run python scripts/record_demo.py --answers    # also answers; needs the real model set up
                                                      # (FARMTWIN_LLAMA_SERVER_BIN, FARMTWIN_LLM_MODEL_PATH)

Writes apps/web/src/demo/fixtures.json. Answers already recorded are kept when run without --answers.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "apps/web/src/demo/fixtures.json"
# the questions the ask box suggests (apps/web/src/components/AskPanel.tsx)
QUESTIONS = ["What should I do this week?", "Is my crop at risk from the recent weather?"]


def record_answer(client, farm_id: int, question: str) -> list[dict]:
    """The stream's events with the delay before each, so the demo replays at the real pace."""
    events, last = [], time.monotonic()
    with client.stream("POST", "/api/ask/stream", json={"farm_id": farm_id, "question": question}) as res:
        for line in res.iter_lines():
            if not line.startswith("data:"):
                continue
            now = time.monotonic()
            events.append({"after_ms": round((now - last) * 1000), "event": json.loads(line[5:])})
            last = now
    return events


def wait_for_model(client, timeout_s: int = 600) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = client.get("/api/model/status").json()["state"]
        if state == "ready":
            return
        if state in ("stopped", "not_set_up"):
            sys.exit(
                f"The model isn't available ({state}). Set FARMTWIN_LLAMA_SERVER_BIN and FARMTWIN_LLM_MODEL_PATH."
            )
        time.sleep(2)
    sys.exit("The model didn't start in time.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", action="store_true", help="also record the real model's answers")
    args = parser.parse_args()

    # a fresh, empty data folder so the demo shows exactly the sample farm
    os.environ["FARMTWIN_DATA_DIR"] = tempfile.mkdtemp(prefix="farmtwin-demo-")
    from fastapi.testclient import TestClient

    from app.main import app

    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    with TestClient(app) as client:
        farm = client.post("/api/farms/sample").json()
        fid = farm["id"]
        data = {
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "farms": client.get("/api/farms").json(),
            "summaries": client.get("/api/farms/summary").json(),
            "farm": client.get(f"/api/farms/{fid}").json(),
            "dashboard": client.get(f"/api/farms/{fid}/dashboard").json(),
            "answers": previous.get("answers", {}),
        }
        if args.answers:
            from app.rag.index import sync_index

            sync_index()
            wait_for_model(client)
            data["answers"] = {q: record_answer(client, fid, q) for q in QUESTIONS}
            data["answers_recorded_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        elif "answers_recorded_at" in previous:
            data["answers_recorded_at"] = previous["answers_recorded_at"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(data['answers'])} recorded answers)")


if __name__ == "__main__":
    main()
