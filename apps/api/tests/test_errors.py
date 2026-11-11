import httpx
import pytest

from app.api import ask as ask_module
from app.errors import AppError
from app.rag.embedder import EMBEDDER_MISSING


def assert_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return body["error"]


def test_missing_farm_uses_the_shared_shape(client):
    assert_error(client.get("/api/farms/999999"), 404, "farm_not_found")


def test_validation_errors_name_the_field(client):
    error = assert_error(client.post("/api/farms", json={}), 422, "invalid_input")
    assert "name" in error["details"]["fields"]


def test_unknown_route_uses_the_shared_shape(client):
    assert_error(client.get("/api/nothing-here"), 404, "not_found")


def test_model_down_is_reported_plainly(client, monkeypatch):
    farm = client.post("/api/farms", json={"name": "Test farm"}).json()
    field = client.post("/api/fields", json={"farm_id": farm["id"], "name": "Main field"}).json()
    client.post(
        "/api/plantings",
        json={
            "field_id": field["id"],
            "crop_type": "maize",
            "planting_date": "2026-10-01",
            "status": "active",
        },
    )

    def offline(*args, **kwargs):
        raise httpx.ConnectError("connection refused on 127.0.0.1:8080")

    found = ask_module.retriever.Retrieval([{"chunk_id": 1, "content": "c"}], 0.5)
    monkeypatch.setattr(ask_module.retriever, "retrieve", lambda *a, **k: found)
    monkeypatch.setattr(ask_module.llm_client, "generate", offline)
    error = assert_error(
        client.post("/api/ask", json={"farm_id": farm["id"], "question": "What now?"}),
        503,
        "model_unavailable",
    )
    assert "127.0.0.1" not in error["message"]


def _farm_with_maize(client):
    farm = client.post("/api/farms", json={"name": "Test farm"}).json()
    field = client.post("/api/fields", json={"farm_id": farm["id"], "name": "Main field"}).json()
    client.post(
        "/api/plantings",
        json={
            "field_id": field["id"],
            "crop_type": "maize",
            "planting_date": "2026-10-01",
            "status": "active",
        },
    )
    return farm


def test_question_outside_the_sources_is_answered_without_the_model(client, monkeypatch):
    farm = _farm_with_maize(client)
    nothing = ask_module.retriever.Retrieval([], 0.9)
    monkeypatch.setattr(ask_module.retriever, "retrieve", lambda *a, **k: nothing)
    monkeypatch.setattr(ask_module.llm_client, "generate", lambda *a, **k: pytest.fail("model was called"))
    res = client.post("/api/ask", json={"farm_id": farm["id"], "question": "How do I prune cocoa?"})
    assert res.status_code == 200
    assert res.json()["narrative"] == ask_module.NOT_IN_SOURCES


def test_missing_search_model_is_reported_plainly(client, monkeypatch):
    farm = _farm_with_maize(client)

    def missing(_):
        raise AppError(503, EMBEDDER_MISSING, "FarmTwin's search model is missing.")

    monkeypatch.setattr(ask_module.retriever, "embed_query", missing)
    assert_error(
        client.post("/api/ask", json={"farm_id": farm["id"], "question": "What now?"}), 503, EMBEDDER_MISSING
    )
