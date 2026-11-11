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
