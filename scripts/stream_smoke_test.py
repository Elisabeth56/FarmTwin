"""Day 5 SSE smoke test.

POSTs to /api/ask/stream and prints each event as it arrives.

Preconditions:
  - Backend running at http://127.0.0.1:8000
  - llama-server running at http://127.0.0.1:8080 (otherwise you'll see a
    single {"type": "error", ...} event, which is a valid clean exit)

Run:
    python scripts/stream_smoke_test.py
"""

from __future__ import annotations

import json
import sys
import time

import httpx


BACKEND_URL = "http://127.0.0.1:8000/api/ask/stream"
FARM_ID = 1
QUESTION = (
    "Heavy rainfall and high humidity in the last 48 hours. "
    "What should this farmer do this week?"
)


def main() -> int:
    payload = {"farm_id": FARM_ID, "question": QUESTION}

    events_total = 0
    tokens_total = 0
    tokens_chars = 0
    t_start = time.time()
    t_first_token = None
    saw_error = False
    saw_ready = False
    saw_recommendation = False

    print(f"POST {BACKEND_URL}")
    print(f"payload: {json.dumps(payload)}\n")

    try:
        with httpx.stream(
            "POST",
            BACKEND_URL,
            json=payload,
            timeout=httpx.Timeout(600.0),
            headers={"Accept": "text/event-stream"},
        ) as resp:
            if resp.status_code != 200:
                print(f"[HTTP {resp.status_code}] {resp.read().decode('utf-8', 'replace')}")
                return 2

            buffer = ""
            for chunk in resp.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    raw_event, buffer = buffer.split("\n\n", 1)
                    data_lines = []
                    for line in raw_event.split("\n"):
                        line = line.lstrip()
                        if line.startswith("data:"):
                            data_lines.append(line[5:].lstrip())
                    if not data_lines:
                        continue
                    try:
                        event = json.loads("\n".join(data_lines))
                    except json.JSONDecodeError as e:
                        print(f"[bad JSON: {e}] {data_lines!r}")
                        continue

                    events_total += 1
                    etype = event.get("type")
                    elapsed = time.time() - t_start

                    if etype == "ready":
                        saw_ready = True
                        chunks = event.get("cited_chunks", [])
                        print(f"[{elapsed:6.2f}s] ready — {len(chunks)} chunks pre-loaded")
                    elif etype == "token":
                        content = event.get("content", "")
                        tokens_total += 1
                        tokens_chars += len(content)
                        if t_first_token is None:
                            t_first_token = elapsed
                            print(f"[{elapsed:6.2f}s] first token")
                        sys.stdout.write(content)
                        sys.stdout.flush()
                    elif etype == "recommendation_ready":
                        saw_recommendation = True
                        recs = event.get("recommendations", [])
                        saved = event.get("saved_recommendation_ids", [])
                        print(
                            f"\n[{elapsed:6.2f}s] recommendation_ready — "
                            f"{len(recs)} recs, saved ids: {saved}"
                        )
                        print(f"  model: {event.get('model_name')}")
                        print(f"  timing_ms: {event.get('timing_ms')}")
                    elif etype == "error":
                        saw_error = True
                        print(f"[{elapsed:6.2f}s] error: {event.get('message')}")
                    else:
                        print(f"[{elapsed:6.2f}s] unknown event type: {etype!r} — {event}")
    except httpx.ConnectError as e:
        print(f"Cannot reach backend at {BACKEND_URL}: {e}")
        return 3
    except KeyboardInterrupt:
        print("\n(interrupted)")
        return 130

    wall = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"Total events:        {events_total}")
    print(f"Token events:        {tokens_total}")
    print(f"Token chars:         {tokens_chars}")
    print(f"Wall clock:          {wall:.2f}s")
    if t_first_token is not None:
        print(f"Time to first token: {t_first_token:.2f}s")
    print(f"Saw ready:           {saw_ready}")
    print(f"Saw recommendation:  {saw_recommendation}")
    print(f"Saw error:           {saw_error}")

    if saw_error and not saw_recommendation:
        # Error was emitted cleanly (e.g. llama-server off). Not a script failure.
        return 0
    if not saw_recommendation:
        print("WARNING: stream ended without recommendation_ready event")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
