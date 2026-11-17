from tests.conftest import API_KEY, make_node, make_segment


async def make_point(client, taxonomy, name="Charyn Canyon", lat=43.35, lon=79.08, **extra) -> dict:
    resp = await client.post("/api/tourist-points", headers=API_KEY, json={
        "name": name, "latitude": lat, "longitude": lon, **taxonomy, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def connect(client, point_id, node_id, access_type="taxi", **fields) -> dict:
    resp = await client.post("/api/point-nodes", headers=API_KEY, json={
        "tourist_point_id": point_id, "node_id": node_id, "access_type": access_type, **fields})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_new_point_becomes_routable_with_auto_connect(client, geo, taxonomy):
    """The whole admin workflow: node → segment → point → auto-connect → route."""
    geo.places["Kolsai Lakes"] = (42.9844, 78.3250)
    almaty = await make_node(client, "Almaty", 43.2335, 76.9218)
    saty = await make_node(client, "Saty", 43.06, 78.40, node_type="village")
    far = await make_node(client, "Shymkent", 42.3417, 69.5901)
    await make_segment(client, almaty["id"], saty["id"], "marshrutka")

    point = (await client.post("/api/tourist-points", headers=API_KEY,
                               json={"name": "Kolsai Lakes", **taxonomy})).json()
    assert point["latitude"] == 42.9844 and point["has_route"] is False

    resp = await client.post("/api/point-nodes/auto-connect", headers=API_KEY,
                             json={"tourist_point_id": point["id"]})
    assert resp.status_code == 201, resp.text
    (link,) = resp.json()
    assert link["node_id"] == saty["id"] and link["node_id"] != far["id"]
    assert link["access_type"] == "taxi" and link["time_minutes"] > 0 and float(link["cost"]) > 0

    again = await client.post("/api/point-nodes/auto-connect", headers=API_KEY,
                              json={"tourist_point_id": point["id"]})
    assert again.status_code == 201 and again.json()[0]["node_id"] == almaty["id"]  # next nearest

    route = await client.get("/api/routes/alternatives",
                             params={"from_node": "almaty", "to_tourist_point": "kolsai-lakes"})
    assert route.status_code == 200, route.text
    assert (await client.get(f"/api/tourist-points/{point['id']}")).json()["has_route"] is True


async def test_walkable_node_is_connected_on_foot(client, taxonomy):
    node = await make_node(client, "Turkestan", 43.2973, 68.2517)
    point = await make_point(client, taxonomy, "Yasawi Mausoleum", 43.2977, 68.2600)
    (link,) = (await client.post("/api/point-nodes/auto-connect", headers=API_KEY,
                                 json={"tourist_point_id": point["id"]})).json()
    assert link["node_id"] == node["id"]
    assert link["access_type"] == "walk" and float(link["cost"]) == 0


async def test_fastest_is_not_fooled_by_very_long_segments(client, taxonomy):
    """
    Regression: per-segment scores were clamped at 480 min, so a 14 h train and
    a 9 h bus scored the same on time and "fastest" could return the train.
    """
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    b = await make_node(client, "Shymkent", 42.3417, 69.5901)
    await make_segment(client, a["id"], b["id"], "train", distance_km=1082, time_minutes=840, cost=3000)
    await make_segment(client, a["id"], b["id"], "bus", distance_km=690, time_minutes=540, cost=4000)
    point = await make_point(client, taxonomy, "Fortress", 42.31, 69.60)
    await connect(client, point["id"], b["id"], "walk", distance_km=1, time_minutes=10)

    resp = await client.get("/api/routes", params={
        "from_node": "almaty", "to_tourist_point": "fortress", "time_weight": 1})
    assert resp.status_code == 200, resp.text
    assert resp.json()["route_steps"][0]["transport_mode"] == "bus"

    cheapest = await client.get("/api/routes", params={
        "from_node": "almaty", "to_tourist_point": "fortress", "cost_weight": 1})
    assert cheapest.json()["route_steps"][0]["transport_mode"] == "train"


async def test_partial_weights_are_accepted_and_normalised(client, taxonomy):
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    b = await make_node(client, "Konayev", 43.8667, 77.0667)
    await make_segment(client, a["id"], b["id"], "bus", distance_km=75, time_minutes=90, cost=900)
    point = await make_point(client, taxonomy)
    await connect(client, point["id"], b["id"], distance_km=5)

    # The example from the endpoint's own docs used to fail with "must sum to 1.0"
    resp = await client.get("/api/routes", params={
        "from_node": "almaty", "to_tourist_point": "charyn-canyon",
        "time_weight": 0.6, "cost_weight": 0.4})
    assert resp.status_code == 200, resp.text

    zero = await client.get("/api/routes", params={
        "from_node": "almaty", "to_tourist_point": "charyn-canyon", "time_weight": 0})
    assert zero.status_code == 400


async def test_start_node_that_is_also_the_access_node(client, taxonomy):
    """A node with no outgoing segments must still reach a point attached to itself."""
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    point = await make_point(client, taxonomy, "Kok Tobe", 43.2330, 76.9760)
    await connect(client, point["id"], a["id"], distance_km=6)

    resp = await client.get("/api/routes", params={"from_node": "almaty", "to_tourist_point": "kok-tobe"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["route_steps"] == [] and body["total_distance_km"] == 6


async def test_missing_things_are_404(client, taxonomy):
    assert (await client.get("/api/routes", params={
        "from_node": "nope", "to_tourist_point": "nope"})).status_code == 404
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    b = await make_node(client, "Island", 44.0, 78.0)
    point = await make_point(client, taxonomy)
    await connect(client, point["id"], b["id"], distance_km=5)
    unreachable = await client.get("/api/routes/alternatives", params={
        "from_node": "almaty", "to_tourist_point": "charyn-canyon"})
    assert unreachable.status_code == 404
    assert "No valid route" in unreachable.json()["detail"]
    assert a["slug"] == "almaty"


async def test_route_cache_hits_and_is_cleared_by_a_write(client, taxonomy):
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    b = await make_node(client, "Konayev", 43.8667, 77.0667)
    seg = await make_segment(client, a["id"], b["id"], "bus", distance_km=75, time_minutes=90, cost=900)
    point = await make_point(client, taxonomy)
    await connect(client, point["id"], b["id"], distance_km=5, cost=1000, time_minutes=10)
    params = {"from_node": "almaty", "to_tourist_point": "charyn-canyon"}

    first = await client.get("/api/routes/alternatives", params=params)
    second = await client.get("/api/routes/alternatives", params=params)
    assert first.headers["x-fastapi-cache"] == "MISS"
    assert second.headers["x-fastapi-cache"] == "HIT"       # used to be MISS forever
    assert second.json() == first.json()

    # An admin changes a price → the cached answer must not survive
    await client.put(f"/api/transport-segments/{seg['id']}", headers=API_KEY, json={"cost": 2500})
    third = await client.get("/api/routes/alternatives", params=params)
    assert third.headers["x-fastapi-cache"] == "MISS"
    assert float(third.json()["alternatives"][0]["total_cost"]) == 3500


async def test_deleting_a_point_removes_its_access_links(client, taxonomy):
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    point = await make_point(client, taxonomy)
    await connect(client, point["id"], a["id"], distance_km=5)

    resp = await client.delete(f"/api/tourist-points/{point['id']}", headers=API_KEY)
    assert resp.status_code == 200, resp.text
    assert (await client.get("/api/point-nodes")).json() == []


async def test_updating_a_point_returns_the_new_region(client, taxonomy):
    point = await make_point(client, taxonomy)
    other = (await client.post("/api/regions", headers=API_KEY, json={"name": "Turkestan Region"})).json()
    resp = await client.put(f"/api/tourist-points/{point['id']}", headers=API_KEY,
                            json={"region_id": other["id"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["region"]["name"] == "Turkestan Region"
    assert resp.json()["slug"] == "charyn-canyon"


async def test_region_delete_and_conflicts(client, taxonomy):
    await make_point(client, taxonomy)
    in_use = await client.delete(f"/api/regions/{taxonomy['region_id']}", headers=API_KEY)
    assert in_use.status_code == 409          # still referenced by a tourist point

    spare = (await client.post("/api/regions", headers=API_KEY, json={"name": "Spare"})).json()
    gone = await client.delete(f"/api/regions/{spare['id']}", headers=API_KEY)
    assert gone.status_code == 204 and gone.content == b""


async def test_point_without_coordinates_gives_a_clear_error(client, taxonomy):
    a = await make_node(client, "Almaty", 43.2335, 76.9218)
    point = await make_point(client, taxonomy)
    await client.put(f"/api/tourist-points/{point['id']}", headers=API_KEY,
                     json={"latitude": None, "longitude": None})
    resp = await client.post("/api/point-nodes", headers=API_KEY, json={
        "tourist_point_id": point["id"], "node_id": a["id"], "access_type": "taxi"})
    assert resp.status_code == 422
