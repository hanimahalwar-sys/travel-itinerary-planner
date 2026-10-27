PAYLOAD = {
    "destination": "Jaipur",
    "start_date": "2026-12-05",
    "end_date": "2026-12-08",
    "budget": 40000,
    "currency": "INR",
    "travelers": 2,
    "travel_style": "balanced",
    "accommodation_tier": "mid",
    "interests": ["food", "culture", "sightseeing"],
    "notes": "",
}


def create(client, headers, **overrides):
    return client.post("/api/trips", json={**PAYLOAD, **overrides}, headers=headers)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ai_mode"] == "builtin"
    assert r.json()["storage"] == "local"


def test_requires_user_header(client):
    assert client.get("/api/trips").status_code == 401


def test_create_trip_structure_and_budget(client, headers):
    r = create(client, headers)
    assert r.status_code == 201
    trip = r.json()
    days = trip["itinerary"]["days"]
    assert len(days) == 4
    assert [d["day"] for d in days] == [1, 2, 3, 4]
    assert all(len(d["activities"]) >= 3 for d in days)
    # total stays within budget (a 10% buffer is kept)
    assert 0 < trip["itinerary"]["total_cost"] <= PAYLOAD["budget"]
    # last day has no hotel night
    assert days[-1]["stay_cost"] == 0
    assert trip["itinerary"]["generated_by"] == "builtin"


def test_no_repeated_activities_within_trip(client, headers):
    trip = create(client, headers).json()
    titles = [a["title"] for d in trip["itinerary"]["days"] for a in d["activities"]]
    assert len(titles) == len(set(titles))


def test_pace_changes_activity_count(client, headers):
    relaxed = create(client, headers, travel_style="relaxed").json()
    packed = create(client, headers, travel_style="packed").json()
    r = sum(len(d["activities"]) for d in relaxed["itinerary"]["days"])
    p = sum(len(d["activities"]) for d in packed["itinerary"]["days"])
    assert p > r


def test_validation_errors(client, headers):
    assert create(client, headers, end_date="2026-12-01").status_code == 422
    assert create(client, headers, budget=0).status_code == 422
    assert create(client, headers, end_date="2027-02-01").status_code == 422  # > 14 days


def test_list_get_delete_and_isolation(client, headers):
    trip = create(client, headers).json()
    ids = [t["id"] for t in client.get("/api/trips", headers=headers).json()]
    assert trip["id"] in ids
    assert client.get(f"/api/trips/{trip['id']}", headers=headers).status_code == 200

    other = {"X-User-Id": "someone-else-99"}
    assert client.get(f"/api/trips/{trip['id']}", headers=other).status_code == 404

    assert client.delete(f"/api/trips/{trip['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/trips/{trip['id']}", headers=headers).status_code == 404


def test_edit_recomputes_costs(client, headers):
    trip = create(client, headers).json()
    itin = trip["itinerary"]
    itin["days"][0]["activities"][0]["cost"] = 1000
    itin["days"][0]["activities"][0]["title"] = "My custom stop"
    r = client.put(f"/api/trips/{trip['id']}", json={"itinerary": itin}, headers=headers)
    assert r.status_code == 200
    saved = r.json()
    d0 = saved["itinerary"]["days"][0]
    assert d0["activities"][0]["title"] == "My custom stop"
    expected = sum(a["cost"] for a in d0["activities"]) + d0["stay_cost"] + d0["transport_cost"]
    assert d0["day_cost"] == expected
    assert saved["itinerary"]["total_cost"] == sum(d["day_cost"] for d in saved["itinerary"]["days"])


def test_regenerate_day_only_changes_that_day(client, headers):
    trip = create(client, headers).json()
    before = trip["itinerary"]["days"]
    r = client.post(f"/api/trips/{trip['id']}/days/2/regenerate", json={}, headers=headers)
    assert r.status_code == 200
    after = r.json()["itinerary"]["days"]
    assert after[0] == before[0] and after[2] == before[2] and after[3] == before[3]
    assert client.post(f"/api/trips/{trip['id']}/days/9/regenerate", json={}, headers=headers).status_code == 404


def test_regenerate_whole_trip(client, headers):
    trip = create(client, headers).json()
    r = client.post(f"/api/trips/{trip['id']}/regenerate", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["itinerary"]["days"]) == 4


def test_single_day_trip(client, headers):
    r = create(client, headers, end_date="2026-12-05")
    assert r.status_code == 201
    day = r.json()["itinerary"]["days"][0]
    assert day["stay_cost"] == 0 and len(day["activities"]) >= 3
