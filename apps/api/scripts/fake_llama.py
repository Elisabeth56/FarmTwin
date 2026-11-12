"""A stand-in for llama-server for working on the UI without the model. Streams a fixed answer
in the OpenAI chat format, slowly enough to see the streaming and to try Stop.

    uv run python scripts/fake_llama.py      # listens on 127.0.0.1:8080
    FARMTWIN_LLAMA_SERVER_BIN=scripts/fake_llama.sh FARMTWIN_LLM_MODEL_PATH=<any file> pnpm dev:api

Not used by the app or the tests; never ship it.
"""

import asyncio
import json
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

ANSWER = (
    "Heavy rain two days ago and humidity above 80% put the vegetative maize in Main field at "
    "high risk of leaf disease [K1]. Check the lower leaves for long grey-green lesions [K2]. "
    "The cowpea in East plot is flowering, the stage when thrips and Maruca do the most damage [K3].\n\n"
    "```json\n"
    '{"recommendations": ['
    '{"what": "Scout Main field for leaf lesions today", "why": "Wet leaves after heavy rain let fungal disease start", '
    '"when_urgency": "immediate", "risk_if_ignored": "A missed patch can spread across the field", "priority": "high"},'
    '{"what": "Check cowpea flowers in East plot for thrips and Maruca", "why": "Flowering is when they cut yield most", '
    '"when_urgency": "this_week", "risk_if_ignored": "Pod loss", "priority": "high"},'
    '{"what": "Log rain after each storm", "why": "Risks are worked out from your logs", '
    '"when_urgency": "monitor", "risk_if_ignored": "Risks go stale", "priority": "low"}'
    "]}\n```"
)

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    words = ANSWER.split(" ")
    if not body.get("stream"):
        return {"choices": [{"message": {"content": " ".join(words)}}], "timings": {}}

    async def tokens():
        for i, word in enumerate(words):
            chunk = {"choices": [{"delta": {"content": word + (" " if i < len(words) - 1 else "")}}]}
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(float(os.environ.get("FAKE_LLAMA_DELAY", "0.06")))
        yield 'data: {"choices": [{"delta": {}}], "timings": {"predicted_ms": 1}}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(tokens(), media_type="text/event-stream")


if __name__ == "__main__":
    import argparse

    # accepts llama-server's flags so the API can supervise it like the real thing (ADR-027)
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args, _ = parser.parse_known_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
