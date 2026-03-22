"""
Distance Estimation Service

Calculates distance_km between two geographic coordinates
based on transport mode, using the most appropriate strategy:

    PLANE, CABLE_CAR  →  Haversine (great-circle) — travel as-the-crow-flies
    CAR, BUS, TAXI,
    MARSHRUTKA        →  OSRM HTTP API (real road network distance)
    TRAIN             →  Haversine × 1.20 (rail ≈ 20% longer than straight line)

NOTE: time_minutes is intentionally NOT auto-calculated here.
      It must be supplied manually when creating a segment so it
      reflects real schedules (including layovers, boarding, delays).

OSRM SETUP:
    Development  → Public demo: http://router.project-osrm.org
                   ⚠️  Rate-limited, no SLA — for testing only!
    Recommended  → Self-host with Kazakhstan OSM extract:
                   docker run -p 5000:5000 osrm/osrm-backend ...
                   See: https://github.com/Project-OSRM/osrm-backend#using-docker
    Alternative  → OpenRouteService API key (2,000 free req/day):
                   https://openrouteservice.org/dev/#/signup
"""

import math
import logging
from typing import Union
import httpx

from app.enums import TransportMode, AccessType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"
OSRM_TIMEOUT_S = 5.0

# Rail tracks are ~20% longer than straight-line (curves around terrain)
_RAIL_DETOUR_FACTOR = 1.20

# Modes that travel on real road networks → use OSRM
_ROAD_MODES = {
    TransportMode.CAR, TransportMode.BUS, TransportMode.TAXI, TransportMode.MARSHRUTKA,
    AccessType.CAR, AccessType.TAXI, AccessType.BUS, AccessType.SHUTTLE
}
# Modes that travel as-the-crow-flies → use Haversine directly
_AIR_MODES  = {TransportMode.PLANE, TransportMode.CABLE_CAR, AccessType.WALK}


# =============================================================================
# 1. HAVERSINE — great-circle distance
# =============================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Shortest path over the Earth's surface in km.
    """
    R = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


# =============================================================================
# 2. OSRM — real road network distance
# =============================================================================

async def road_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Query OSRM for actual driving distance in km.
    """
    url = f"{OSRM_BASE_URL}/{lon1},{lat1};{lon2},{lat2}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params={"overview": "false", "steps": "false"},
                timeout=OSRM_TIMEOUT_S,
            )
            resp.raise_for_status()
            metres = resp.json()["routes"][0]["legs"][0]["distance"]
            return round(metres / 1000, 2)
    except Exception as exc:
        logger.warning("OSRM unavailable (%s) — falling back to Haversine × 1.35", exc)
        return round(haversine_km(lat1, lon1, lat2, lon2) * 1.35, 2)


# =============================================================================
# 3. MAIN ENTRY POINT
# =============================================================================

async def estimate_distance(
    from_lat: float, from_lon: float,
    to_lat: float,   to_lon: float,
    mode: Union[TransportMode, AccessType],
) -> float:
    """
    Return distance_km between two coordinate pairs using the correct
    strategy for the given transport mode or access type.
    """
    if mode in _AIR_MODES:
        return haversine_km(from_lat, from_lon, to_lat, to_lon)

    if mode in _ROAD_MODES:
        return await road_distance_km(from_lat, from_lon, to_lat, to_lon)

    # TRAIN / Default
    return round(haversine_km(from_lat, from_lon, to_lat, to_lon) * _RAIL_DETOUR_FACTOR, 2)
