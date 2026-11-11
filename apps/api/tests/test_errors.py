import httpx

from app.api import ask as ask_module


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

    monkeypatch.setattr(ask_module.retriever, "retrieve_chunks", lambda *a, **k: [])
    monkeypatch.setattr(ask_module.llm_client, "generate", offline)
    error = assert_error(
        client.post("/api/ask", json={"farm_id": farm["id"], "question": "What now?"}),
        503,
        "model_unavailable",
    )
    assert "127.0.0.1" not in error["message"]
