"""
Test setup.

The environment is configured BEFORE the app is imported, because
app.core.config builds `settings` (and app.core.database builds the engine)
at import time.

No test touches the network: OSRM and Nominatim are replaced by an
httpx.MockTransport, so the suite is fast and deterministic.
"""

import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="nomad-tests-")
# Environment variables win over a developer's local .env file, so blanking the
# Postgres settings guarantees the tests can never run against a real database.
os.environ.update({
    "POSTGRES_USER": "", "POSTGRES_PASSWORD": "", "POSTGRES_SERVER": "", "POSTGRES_DB": "",
    "SQLITE_URL": f"sqlite+aiosqlite:///{_tmp_dir}/test.db",
    "TEAM_API_KEY": "test-key",
    "SECRET_KEY": "test-secret",
    "ENABLE_ADMIN": "false",
    "DEBUG": "false",
    "OSRM_BASE_URL": "https://osrm.test",
    "NOMINATIM_BASE_URL": "https://nominatim.test",
    "TRUSTED_PROXY_COUNT": "1",
})

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi_cache import FastAPICache  # noqa: E402
from fastapi_cache.backends.inmemory import InMemoryBackend  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Region, TouristPointCategory  # noqa: E402
from app.services import distance  # noqa: E402

API_KEY = {"X-API-Key": "test-key"}


class FakeGeo:
    """Programmable stand-in for OSRM + Nominatim."""

    def __init__(self):
        self.osrm_up = True
        self.osrm_calls = 0
        self.osrm_km = 100.0
        self.osrm_minutes = 90.0
        self.places = {}  # name -> (lat, lon)

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "osrm.test":
            self.osrm_calls += 1
            if not self.osrm_up:
                return httpx.Response(503)
            return httpx.Response(200, json={"routes": [{
                "distance": self.osrm_km * 1000, "duration": self.osrm_minutes * 60,
            }]})
        if request.url.host == "nominatim.test":
            hit = self.places.get(request.url.params["q"])
            return httpx.Response(200, json=[{"lat": str(hit[0]), "lon": str(hit[1])}] if hit else [])
        return httpx.Response(404)


@pytest.fixture(autouse=True)
async def fresh_state(monkeypatch):
    """Empty database, empty caches and a fake geo backend for every test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    await FastAPICache.clear()
    distance._osrm_cache.clear()

    geo = FakeGeo()
    client = httpx.AsyncClient(transport=httpx.MockTransport(geo.handler))
    monkeypatch.setattr(distance, "get_http_client", lambda: client)
    # coordinates.py imported the function by name, so patch that reference too
    from app.services import coordinates
    monkeypatch.setattr(coordinates, "get_http_client", lambda: client)
    yield geo
    await client.aclose()


@pytest.fixture
def geo(fresh_state) -> FakeGeo:
    return fresh_state


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def taxonomy():
    """A region and a category, required by every tourist point."""
    async with SessionLocal(expire_on_commit=False) as db:
        region, category = Region(name="Almaty Region"), TouristPointCategory(name="Nature")
        db.add_all([region, category])
        await db.commit()
        return {"region_id": region.id, "category_id": category.id}


async def make_node(client, name, lat, lon, node_type="city") -> dict:
    resp = await client.post("/api/transport-nodes", headers=API_KEY, json={
        "name": name, "latitude": lat, "longitude": lon, "node_type": node_type,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def make_segment(client, from_id, to_id, mode, **fields) -> dict:
    resp = await client.post("/api/transport-segments", headers=API_KEY, json={
        "from_node_id": from_id, "to_node_id": to_id, "transport_mode": mode, **fields,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()
