from tests.conftest import API_KEY, make_node, make_segment


async def two_cities(client):
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    b = await make_node(client, "Konayev", 43.8667, 77.0667)
    return a, b


async def test_writes_require_api_key(client):
    resp = await client.post("/api/transport-nodes", json={
        "name": "X", "latitude": 1, "longitude": 1, "node_type": "city"})
    assert resp.status_code == 403
    # A non-ASCII key used to crash secrets.compare_digest with a 500
    resp = await client.post("/api/transport-nodes", headers={"X-API-Key": "kéy".encode()}, json={
        "name": "X", "latitude": 1, "longitude": 1, "node_type": "city"})
    assert resp.status_code == 403


async def test_create_segment_with_only_nodes_and_mode(client, geo):
    a, b = await two_cities(client)
    geo.osrm_km, geo.osrm_minutes = 75.0, 60.0

    seg = await make_segment(client, a["id"], b["id"], "bus")

    assert seg["distance_km"] == 75.0
    assert seg["time_minutes"] == 75              # 60 min driving × 1.25 for a bus
    assert float(seg["cost"]) == 900              # 500 + 5.5 × 75 = 912.5 → 900
    assert seg["co2_kg"] == round(0.089 * 75, 3)
    assert seg["comfort_score"] == 5.5


async def test_supplied_values_win_over_estimates(client, geo):
    a, b = await two_cities(client)
    seg = await make_segment(client, a["id"], b["id"], "bus", cost=5000, time_minutes=90, distance_km=75)
    assert float(seg["cost"]) == 5000 and seg["time_minutes"] == 90
    assert geo.osrm_calls == 0   # distance was given → no external call needed


async def test_estimate_reports_fallback_when_osrm_is_down(client, geo):
    a, b = await two_cities(client)
    geo.osrm_up = False
    resp = await client.post("/api/transport-segments/estimate", headers=API_KEY, json={
        "from_node_id": a["id"], "to_node_id": b["id"], "transport_mode": "taxi"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["distance_strategy"] == "haversine_fallback"
    assert body["time_strategy"] == "speed_model"
    assert body["distance_km"] > 0 and body["time_minutes"] > 0 and float(body["cost"]) > 0


async def test_estimate_then_create_hits_osrm_once(client, geo):
    a, b = await two_cities(client)
    payload = {"from_node_id": a["id"], "to_node_id": b["id"], "transport_mode": "taxi"}
    await client.post("/api/transport-segments/estimate", headers=API_KEY, json=payload)
    await client.post("/api/transport-segments", headers=API_KEY, json=payload)
    assert geo.osrm_calls == 1


async def test_estimate_requires_api_key(client):
    resp = await client.post("/api/transport-segments/estimate", json={
        "from_node_id": 1, "to_node_id": 2, "transport_mode": "taxi"})
    assert resp.status_code == 403


async def test_create_reverse_makes_both_directions(client):
    a, b = await two_cities(client)
    await make_segment(client, a["id"], b["id"], "taxi", create_reverse=True)
    segments = (await client.get("/api/transport-segments")).json()
    assert {(s["from_node_id"], s["to_node_id"]) for s in segments} == {
        (a["id"], b["id"]), (b["id"], a["id"])}


async def test_duplicate_and_self_loop_are_client_errors_not_500(client):
    a, b = await two_cities(client)
    await make_segment(client, a["id"], b["id"], "bus")
    dup = await client.post("/api/transport-segments", headers=API_KEY, json={
        "from_node_id": a["id"], "to_node_id": b["id"], "transport_mode": "bus"})
    assert dup.status_code == 409
    loop = await client.post("/api/transport-segments", headers=API_KEY, json={
        "from_node_id": a["id"], "to_node_id": a["id"], "transport_mode": "bus"})
    assert loop.status_code == 422


async def test_price_check_flags_only_outliers(client):
    a, b = await two_cities(client)
    # model price for a 75 km bus is 900 KZT
    await make_segment(client, a["id"], b["id"], "bus", distance_km=75, cost=1000)   # +11% → fine
    await make_segment(client, b["id"], a["id"], "bus", distance_km=75, cost=5000)   # way off

    resp = await client.get("/api/transport-segments/price-check?threshold_pct=30", headers=API_KEY)
    body = resp.json()
    assert resp.status_code == 200
    assert body["checked_count"] == 2 and body["flagged_count"] == 1
    item = body["flagged"][0]
    assert float(item["stored_cost"]) == 5000 and float(item["estimated_cost"]) == 900
    assert item["deviation_pct"] > 400
    assert item["from_node"] == "Konayev"


async def test_recalculate_overwrites_only_named_fields(client):
    a, b = await two_cities(client)
    seg = await make_segment(client, a["id"], b["id"], "bus", distance_km=75, cost=5000, time_minutes=999)

    resp = await client.post(f"/api/transport-segments/{seg['id']}/recalculate",
                             headers=API_KEY, json={"fields": ["cost"]})
    body = resp.json()
    assert resp.status_code == 200
    assert float(body["cost"]) == 900
    assert body["time_minutes"] == 999   # untouched

    empty = await client.post(f"/api/transport-segments/{seg['id']}/recalculate",
                              headers=API_KEY, json={"fields": []})
    assert empty.status_code == 422


async def test_delete_node_in_use_is_refused(client):
    a, b = await two_cities(client)
    await make_segment(client, a["id"], b["id"], "bus")
    resp = await client.delete(f"/api/transport-nodes/{a['id']}", headers=API_KEY)
    assert resp.status_code == 409


async def test_updating_a_node_keeps_its_custom_slug(client):
    resp = await client.post("/api/transport-nodes", headers=API_KEY, json={
        "name": "Almaty International Airport", "slug": "almaty-airport",
        "latitude": 43.35, "longitude": 77.04, "node_type": "airport"})
    node = resp.json()
    patched = await client.patch(f"/api/transport-nodes/{node['id']}", headers=API_KEY,
                                 json={"latitude": 43.3521})
    assert patched.status_code == 200
    assert patched.json()["slug"] == "almaty-airport"


async def test_node_is_geocoded_when_coordinates_missing(client, geo):
    geo.places["Taraz"] = (42.9, 71.3667)
    ok = await client.post("/api/transport-nodes", headers=API_KEY,
                           json={"name": "Taraz", "node_type": "city"})
    assert ok.status_code == 201 and ok.json()["latitude"] == 42.9
    missing = await client.post("/api/transport-nodes", headers=API_KEY,
                                json={"name": "Nowhereville", "node_type": "city"})
    assert missing.status_code == 422
