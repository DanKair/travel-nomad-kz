"""
Distance & Time Estimation Service

Calculates distance_km and time_minutes between two geographic coordinates
based on the transport mode, using the most appropriate strategy per mode:

    PLANE, CABLE_CAR  →  Haversine (great-circle) — they travel as-the-crow-flies
    CAR, BUS, TAXI,
    MARSHRUTKA        →  OSRM HTTP API (real road network distance)
    TRAIN             →  Haversine × RAIL_DETOUR_FACTOR (track ≈ 20% longer)

Time is always derived from distance using per-mode speed constants:
    time_minutes = ceil((distance_km / SPEED_KMH[mode]) * 60)

OSRM SETUP (required for road modes):
    Development  → Use public demo: http://router.project-osrm.org
                   ⚠️ Rate-limited, no SLA, not for production!
    Recommended  → Self-host with Kazakhstan OSM extract:
                   docker run -p 5000:5000 osrm/osrm-backend ...
                   See: https://github.com/Project-OSRM/osrm-backend#using-docker
    Alternative  → OpenRouteService API key (2,000 free req/day):
                   https://openrouteservice.org/dev/#/signup
"""

import math
import logging
from typing import Optional
import httpx

from app.enums import TransportMode, AccessType
from app.constants import (
    SPEED_KMH,
    ACCESS_SPEED_KMH,
    RAIL_DETOUR_FACTOR,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — swap these for self-hosted OSRM or ORS in production
# ---------------------------------------------------------------------------
OSRM_BASE_URL = "http://router.project-osrm.org"
OSRM_TIMEOUT_S = 5.0

# Modes that travel on real road networks (use OSRM)
_ROAD_MODES = {TransportMode.CAR, TransportMode.BUS, TransportMode.TAXI, TransportMode.MARSHRUTKA}
# Modes that travel as-the-crow-flies (use Haversine directly)
_AIR_MODES   = {TransportMode.PLANE, TransportMode.CABLE_CAR}
# TRAIN uses Haversine × detour factor (defined by exclusion)


# =============================================================================
# 1. HAVERSINE  —  great-circle distance between two lat/lon points
# =============================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return the shortest path over the Earth's surface (in km).

    This is the correct formula for PLANE and CABLE_CAR distances.
    For trains and roads it underestimates (tracks/roads aren't straight).

    Formula reference: https://www.movable-type.co.uk/scripts/latlong.html
    """
    R = 6_371.0  # Earth's mean radius in km

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 2)


# =============================================================================
# 2. OSRM  —  real road network distance via HTTP
# =============================================================================

async def road_distance_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Query OSRM for the actual driving distance between two coordinates.

    OSRM coordinates are (longitude, latitude) — note the reversed order!
    Returns distance in km.

    Falls back to Haversine × 1.35 (road detour factor) if OSRM is unreachable.
    """
    # OSRM route endpoint: /route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}
    url = (
        f"{OSRM_BASE_URL}/route/v1/driving"
        f"/{lon1},{lat1};{lon2},{lat2}"
    )
    params = {
        "overview": "false",   # we only need distance, not full geometry
        "steps": "false",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=OSRM_TIMEOUT_S)
            response.raise_for_status()
            data = response.json()

        # OSRM returns distance in METRES
        distance_m = data["routes"][0]["legs"][0]["distance"]
        return round(distance_m / 1000, 2)

    except Exception as exc:
        logger.warning(
            "OSRM unavailable (%s). Falling back to Haversine × 1.35 for road distance.",
            exc
        )
        # Road detour factor: roads are ~35% longer than straight-line on average
        return round(haversine_km(lat1, lon1, lat2, lon2) * 1.35, 2)


# =============================================================================
# 3. MAIN ENTRY POINT — used by the API layer
# =============================================================================

async def estimate_segment(
    from_lat: float, from_lon: float,
    to_lat: float,   to_lon: float,
    mode: TransportMode,
) -> dict:
    """
    Estimate distance_km and time_minutes for a transport segment.

    Strategy selection:
        PLANE / CABLE_CAR  →  Haversine (straight line)
        CAR / BUS / TAXI / MARSHRUTKA  →  OSRM (road network)
        TRAIN  →  Haversine × RAIL_DETOUR_FACTOR (1.20)

    Returns:
        { "distance_km": float, "time_minutes": int }
    """
    # --- Step 1: compute distance ---
    if mode in _AIR_MODES:
        distance_km = haversine_km(from_lat, from_lon, to_lat, to_lon)

    elif mode in _ROAD_MODES:
        distance_km = await road_distance_km(from_lat, from_lon, to_lat, to_lon)

    else:
        # TRAIN (and any future non-road, non-air modes)
        straight = haversine_km(from_lat, from_lon, to_lat, to_lon)
        distance_km = round(straight * RAIL_DETOUR_FACTOR, 2)

    # --- Step 2: derive time from distance + mode speed ---
    speed = SPEED_KMH[mode]
    time_minutes = math.ceil((distance_km / speed) * 60)

    return {
        "distance_km": distance_km,
        "time_minutes": time_minutes,
    }


def estimate_access(
    distance_km: float,
    access_type: AccessType,
) -> int:
    """
    Derive time_minutes for last-mile access from distance and access type.
    This is synchronous (no OSRM needed — last-mile trips are short + local).

    Returns: time_minutes (int)
    """
    speed = ACCESS_SPEED_KMH.get(access_type, 20.0)
    return math.ceil((distance_km / speed) * 60)
