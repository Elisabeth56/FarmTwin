from datetime import date, timedelta


def make_farm(client, name="Adamu's farm"):
    return client.post("/api/farms", json={"name": name, "region": "Zaria"}).json()


def make_field(client, farm_id, name="Main field"):
    return client.post("/api/fields", json={"farm_id": farm_id, "name": name, "area_hectares": 1.2}).json()


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def test_intercropped_field_shows_both_plantings(client):
    farm = make_farm(client)
    field = make_field(client, farm["id"])
    for crop, planted in [("maize", 38), ("cowpea", 41)]:
        r = client.post(
            "/api/plantings",
            json={"field_id": field["id"], "crop_type": crop, "planting_date": days_ago(planted)},
        )
        assert r.status_code == 201

    overview = client.get(f"/api/farms/{farm['id']}/overview").json()
    plantings = overview["fields"][0]["plantings"]
    assert [p["crop_type"] for p in plantings] == ["maize", "cowpea"]
    assert [p["days_since_planting"] for p in plantings] == [38, 41]
    assert plantings[0]["stage"]  # maize has a calendar today; cowpea gets one in #9


def test_lists_are_scoped_to_one_farm(client):
    a, b = make_farm(client, "Farm A"), make_farm(client, "Farm B")
    field_a, field_b = make_field(client, a["id"]), make_field(client, b["id"])
    client.post("/api/plantings", json={"field_id": field_a["id"], "crop_type": "maize"})
    client.post("/api/plantings", json={"field_id": field_b["id"], "crop_type": "rice"})

    fields = client.get("/api/fields", params={"farm_id": a["id"]}).json()
    assert [f["id"] for f in fields] == [field_a["id"]]
    crops = [p["crop_type"] for p in client.get("/api/plantings", params={"farm_id": a["id"]}).json()]
    assert crops == ["maize"]


def test_field_needs_an_existing_farm(client):
    r = client.post("/api/fields", json={"farm_id": 424242, "name": "Nowhere"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "farm_not_found"


def test_unknown_crop_is_rejected_by_name(client):
    field = make_field(client, make_farm(client)["id"])
    r = client.post("/api/plantings", json={"field_id": field["id"], "crop_type": "cocoa"})
    assert r.status_code == 422
    assert "crop_type" in r.json()["error"]["details"]["fields"]


def test_future_planting_date_is_rejected(client):
    field = make_field(client, make_farm(client)["id"])
    r = client.post(
        "/api/plantings", json={"field_id": field["id"], "crop_type": "maize", "planting_date": days_ago(-3)}
    )
    assert r.status_code == 422


def test_logged_observation_can_be_undone(client):
    field = make_field(client, make_farm(client)["id"])
    obs = client.post(
        "/api/observations",
        json={
            "field_id": field["id"],
            "obs_type": "rainfall",
            "value_numeric": 65,
            "unit": "mm",
            "observed_at": "2026-11-11T08:00:00",
        },
    ).json()
    assert client.delete(f"/api/observations/{obs['id']}").status_code == 204
    assert client.get(f"/api/observations/{obs['id']}").status_code == 404


def test_deleting_a_farm_removes_its_fields(client):
    farm = make_farm(client)
    field = make_field(client, farm["id"])
    assert client.delete(f"/api/farms/{farm['id']}").status_code == 204
    assert client.get(f"/api/fields/{field['id']}").status_code == 404


def test_sample_farm_shows_current_risks_in_the_summary(client):
    sample = client.post("/api/farms/sample")
    assert sample.status_code == 201
    summary = next(f for f in client.get("/api/farms/summary").json() if f["id"] == sample.json()["id"])
    assert {p["crop"] for p in summary["plots"]} == {"maize", "cowpea", "sorghum"}
    titles = {r["title"] for r in summary["risks"]}
    assert "Fungal risk after heavy rain" in titles
    assert "Pests at flowering or podding" in titles
    assert summary["risks"][0]["severity"] == "high"
    assert summary["last_logged_at"] is not None


def test_plots_split_a_field_between_its_plantings(client):
    farm = client.post("/api/farms", json={"name": "Intercrop"}).json()
    field = client.post(
        "/api/fields", json={"farm_id": farm["id"], "name": "Main", "area_hectares": 1.0}
    ).json()
    for crop in ("maize", "cowpea"):
        client.post(
            "/api/plantings",
            json={
                "field_id": field["id"],
                "crop_type": crop,
                "planting_date": "2026-10-01",
                "status": "active",
            },
        )
    summary = next(f for f in client.get("/api/farms/summary").json() if f["id"] == farm["id"])
    assert [p["share"] for p in summary["plots"]] == [0.5, 0.5]
    assert summary["last_logged_at"] is None
