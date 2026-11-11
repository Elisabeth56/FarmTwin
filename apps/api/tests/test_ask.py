import json
import logging
from datetime import date, timedelta

import httpx
import pytest

from app.ai import llm
from app.errors import AppError
from app.features.ask import context
from app.rag.embedder import EMBEDDER_MISSING
from app.rag.retriever import Retrieval
from tests.test_errors import assert_error

CHUNKS = [
    {
        "chunk_id": 11,
        "source_id": "a",
        "source_org": "IITA",
        "chunk_title": "Cowpea pests",
        "content": "Spray at bud initiation.",
    },
    {
        "chunk_id": 12,
        "source_id": "b",
        "source_org": "IITA",
        "chunk_title": "Maize harvest",
        "content": "Black layer.",
    },
]
GOOD = (
    "Pests at flowering hit cowpea pods [K1]. Check the maize too [K9].\n\n"
    "```json\n"
    + json.dumps(
        {
            "recommendations": [
                {
                    "what": "Spray the cowpea now",
                    "why": "Flowers are open",
                    "when_urgency": "immediate",
                    "risk_if_ignored": "Pod loss",
                    "priority": "high",
                }
            ]
        }
    )
    + "\n```"
)
BAD = 'Pests at flowering hit cowpea pods [K1].\n\n```json\n{"recommendations": [{"what": "Spray"}]}\n```'


@pytest.fixture()
def farm(client):
    farm = client.post("/api/farms", json={"name": "Ada farm", "region": "Kaduna"}).json()
    north = client.post("/api/fields", json={"farm_id": farm["id"], "name": "North"}).json()
    south = client.post("/api/fields", json={"farm_id": farm["id"], "name": "South"}).json()
    planted = (date.today() - timedelta(days=40)).isoformat()
    for field, crop in ((north, "cowpea"), (north, "maize"), (south, "cassava")):
        client.post(
            "/api/plantings",
            json={"field_id": field["id"], "crop_type": crop, "planting_date": planted, "status": "active"},
        )
    return farm


@pytest.fixture()
def found(monkeypatch):
    calls = []

    def retrieve(query, crops, top_k=6, db_session=None):
        calls.append(crops)
        return Retrieval(CHUNKS, 0.5)

    monkeypatch.setattr(context.retriever, "retrieve", retrieve)
    return calls


@pytest.fixture()
def model(monkeypatch):
    """Replies with the queued answers in order and records every request."""
    replies: list[str] = []
    requests: list[list[dict]] = []

    def generate(messages, max_tokens=600, temperature=0.3):
        requests.append(messages)
        return llm.Completion(replies.pop(0), {"prompt_ms": 5, "predicted_ms": 50})

    async def stream(messages, max_tokens=600, temperature=0.3):
        requests.append(messages)
        for word in replies.pop(0).split(" "):
            yield {"type": "token", "content": word + " "}
        yield {"type": "done", "timings": {}}

    monkeypatch.setattr(llm, "generate", generate)
    monkeypatch.setattr(llm, "stream", stream)
    return replies, requests


def ask(client, farm, question="Insects are on my cowpea flowers"):
    return client.post("/api/ask", json={"farm_id": farm["id"], "question": question})


def stream_events(client, farm):
    res = client.post("/api/ask/stream", json={"farm_id": farm["id"], "question": "Insects on the cowpea"})
    return [json.loads(line[5:]) for line in res.text.splitlines() if line.startswith("data:")]


def test_prompt_covers_every_active_planting_and_searches_all_crops(client, farm, found, model):
    replies, requests = model
    replies.append(GOOD)
    ask(client, farm)
    assert found == [["cassava", "cowpea", "maize"]]
    user = requests[0][1]["content"]
    for text in (
        "cowpea in field 'North'",
        "maize in field 'North'",
        "cassava in field 'South'",
        "[K1] (IITA) Cowpea pests",
    ):
        assert text in user


def test_valid_answer_saves_cards_and_keeps_only_real_citations(client, farm, found, model):
    model[0].append(GOOD)
    body = ask(client, farm).json()
    assert body["narrative"].startswith("Pests at flowering")
    assert "```" not in body["narrative"]
    assert [r["what"] for r in body["recommendations"]] == ["Spray the cowpea now"]
    assert [c["chunk_id"] for c in body["cited_chunks"]] == [11]  # [K9] doesn't exist
    assert len(body["saved_recommendation_ids"]) == 1


def test_invalid_block_gets_one_repair(client, farm, found, model):
    replies, requests = model
    replies.extend([BAD, GOOD])
    body = ask(client, farm).json()
    assert len(requests) == 2
    assert "could not be read" in requests[1][-1]["content"]
    assert body["recommendations"][0]["what"] == "Spray the cowpea now"


def test_failed_repair_still_shows_the_answer_without_cards(client, farm, found, model):
    replies, requests = model
    replies.extend([BAD, "still not json"])
    body = ask(client, farm).json()
    assert len(requests) == 2
    assert body["narrative"].startswith("Pests at flowering")
    assert body["recommendations"] == []
    assert body["saved_recommendation_ids"] == []


def test_question_outside_the_sources_skips_the_model(client, farm, model, monkeypatch):
    monkeypatch.setattr(context.retriever, "retrieve", lambda *a, **k: Retrieval([], 0.9))
    body = ask(client, farm, "How do I prune cocoa?").json()
    assert body["narrative"] == context.NOT_IN_SOURCES
    assert model[1] == []


def test_farm_without_plantings_skips_the_model(client, model):
    farm = client.post("/api/farms", json={"name": "Empty"}).json()
    assert ask(client, farm).json()["narrative"] == context.NO_PLANTING
    assert model[1] == []


def test_prompt_version_and_model_are_logged(client, farm, found, model, caplog):
    model[0].append(GOOD)
    with caplog.at_level(logging.INFO, logger="app.features.ask.answer"):
        ask(client, farm)
    line = next(r.getMessage() for r in caplog.records if r.getMessage().startswith("ask "))
    assert "prompt=ask/v2" in line and "model=qwen2.5-3b-instruct-q4_k_m" in line and "outcome=cards" in line


def test_stream_sends_ready_tokens_then_the_validated_answer(client, farm, found, model):
    model[0].extend([BAD, GOOD])
    events = stream_events(client, farm)
    assert events[0]["type"] == "ready" and len(events[0]["cited_chunks"]) == 2
    assert {e["type"] for e in events[1:-1]} == {"token"}
    final = events[-1]
    assert final["type"] == "recommendation_ready"
    assert final["recommendations"][0]["priority"] == "high"  # came from the repair
    assert "```" not in final["narrative"]


def test_model_down_is_reported_plainly(client, farm, found, monkeypatch):
    def offline(*args, **kwargs):
        raise AppError(503, "model_unavailable", "The AI model isn't running.")

    monkeypatch.setattr(llm, "generate", offline)
    assert_error(ask(client, farm), 503, "model_unavailable")


def test_missing_search_model_is_reported_plainly(client, farm, monkeypatch):
    def missing(_):
        raise AppError(503, EMBEDDER_MISSING, "FarmTwin's search model is missing.")

    monkeypatch.setattr(context.retriever, "embed_query", missing)
    assert_error(ask(client, farm), 503, EMBEDDER_MISSING)


# ---- the llama-server client ----------------------------------------------------------------


def _mock(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(
        llm.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda url, **kw: httpx.Client(transport=httpx.MockTransport(handler)).post(url, **kw),
    )


async def _collect(messages):
    return [e async for e in llm.stream(messages)]


def test_stream_reads_openai_chunks_and_llama_timings(monkeypatch):
    lines = [
        {"choices": [{"delta": {"content": "Hel"}}]},
        {"choices": [{"delta": {"content": "lo"}}]},
        {"choices": [{"delta": {}}], "timings": {"predicted_ms": 12}},
    ]
    body = "".join(f"data: {json.dumps(x)}\n\n" for x in lines) + "data: [DONE]\n\n"

    def handler(request):
        sent = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions" and sent["stream"] is True
        return httpx.Response(200, text=body)

    _mock(monkeypatch, handler)
    import asyncio

    events = asyncio.run(_collect([{"role": "user", "content": "hi"}]))
    assert [e.get("content") for e in events if e["type"] == "token"] == ["Hel", "lo"]
    assert events[-1] == {"type": "done", "timings": {"predicted_ms": 12}}


def test_stream_reports_a_server_error(monkeypatch):
    _mock(monkeypatch, lambda request: httpx.Response(500, text="boom"))
    import asyncio

    events = asyncio.run(_collect([]))
    assert events == [{"type": "error", "code": "model_unavailable", "message": events[0]["message"]}]


def test_generate_returns_content(monkeypatch):
    reply = {"choices": [{"message": {"content": "ok"}}], "timings": {"prompt_ms": 3}}
    _mock(monkeypatch, lambda request: httpx.Response(200, json=reply))
    assert llm.generate([]) == llm.Completion("ok", {"prompt_ms": 3})
