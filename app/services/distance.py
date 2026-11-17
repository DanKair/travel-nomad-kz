"""
Distance Estimation Service

Answers "how far apart are these two coordinates for this way of travelling?"

    PLANE, CABLE_CAR  →  Haversine (great-circle, as the crow flies)
    WALK              →  Haversine × 1.30 (paths are not straight lines)
    TRAIN             →  Haversine × 1.20 (rail curves around terrain)
    CAR, BUS, TAXI,
    MARSHRUTKA,
    SHUTTLE           →  OSRM (real road network), which also returns the
                         driving duration. If OSRM is down we fall back to
                         Haversine × 1.35 and SAY SO in `strategy`.

Every result is a TravelEstimate carrying the strategy that was actually
used, so callers never report "osrm" for a number that was really a fallback.

OSRM: the URL comes from settings.OSRM_BASE_URL. The default is the public
demo server (rate-limited, no SLA). For production, self-host OSRM with the
Kazakhstan extract and point OSRM_BASE_URL at it.
"""

import math
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Union

import httpx

from app.core.config import settings
from app.enums import TransportMode, AccessType

logger = logging.getLogger(__name__)

Mode = Union[TransportMode, AccessType]

# Detour factors: real path length ÷ straight-line length
_RAIL_DETOUR_FACTOR = 1.20
_WALK_DETOUR_FACTOR = 1.30
_ROAD_FALLBACK_FACTOR = 1.35

STRATEGY_HAVERSINE = "haversine"
STRATEGY_DETOUR = "haversine_x_detour"
STRATEGY_OSRM = "osrm"
STRATEGY_OSRM_FALLBACK = "haversine_fallback"  # OSRM was asked but did not answer

# NOTE: TransportMode and AccessType are both `str` enums, so
# TransportMode.TAXI == AccessType.TAXI == "taxi". Membership tests below
# therefore work for either enum.
_ROAD_MODES = {
    TransportMode.CAR, TransportMode.BUS, TransportMode.TAXI, TransportMode.MARSHRUTKA,
    AccessType.CAR, AccessType.TAXI, AccessType.BUS, AccessType.SHUTTLE,
}
_AIR_MODES = {TransportMode.PLANE, TransportMode.CABLE_CAR}


@dataclass(frozen=True)
class TravelEstimate:
    """Result of a distance lookup."""
    distance_km: float
    strategy: str
    # Driving time reported by OSRM (private car, no stops). None when the
    # distance did not come from OSRM.
    driving_minutes: Optional[float] = None


class MissingCoordinatesError(ValueError):
    """Raised when one of the endpoints has no latitude/longitude."""


# =============================================================================
# 1. HAVERSINE — great-circle distance
# =============================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Shortest path over the Earth's surface in km."""
    R = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


# =============================================================================
# 2. OSRM — real road network distance + duration
# =============================================================================

# One shared client = one connection pool. Creating a client per request
# pays a new TCP + TLS handshake every time.
_http_client: Optional[httpx.AsyncClient] = None

# Small in-process memo. An admin typically calls /estimate and then creates
# the segment: same coordinates twice within seconds. Road geometry does not
# change between those calls, so the second one should not hit the network.
_OSRM_CACHE_MAX = 512
_osrm_cache: "OrderedDict[tuple, TravelEstimate]" = OrderedDict()


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=settings.OSRM_TIMEOUT_S,
            headers={"User-Agent": settings.GEOCODER_USER_AGENT},
        )
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None


async def road_travel(lat1: float, lon1: float, lat2: float, lon2: float) -> TravelEstimate:
    """
    Ask OSRM for driving distance and duration.
    Never raises: on any failure returns a Haversine-based fallback whose
    strategy is STRATEGY_OSRM_FALLBACK.
    """
    key = (round(lat1, 5), round(lon1, 5), round(lat2, 5), round(lon2, 5))
    cached = _osrm_cache.get(key)
    if cached is not None:
        _osrm_cache.move_to_end(key)
        return cached

    url = f"{settings.OSRM_BASE_URL.rstrip('/')}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    try:
        resp = await get_http_client().get(url, params={"overview": "false", "steps": "false"})
        resp.raise_for_status()
        route = resp.json()["routes"][0]
        estimate = TravelEstimate(
            distance_km=round(route["distance"] / 1000, 2),
            strategy=STRATEGY_OSRM,
            driving_minutes=round(route["duration"] / 60, 1),
        )
    except Exception as exc:
        logger.warning("OSRM unavailable (%r) — falling back to Haversine × %s", exc, _ROAD_FALLBACK_FACTOR)
        # Fallbacks are NOT cached: the next call should retry OSRM.
        return TravelEstimate(
            distance_km=round(haversine_km(lat1, lon1, lat2, lon2) * _ROAD_FALLBACK_FACTOR, 2),
            strategy=STRATEGY_OSRM_FALLBACK,
        )

    _osrm_cache[key] = estimate
    if len(_osrm_cache) > _OSRM_CACHE_MAX:
        _osrm_cache.popitem(last=False)
    return estimate


# =============================================================================
# 3. MAIN ENTRY POINT
# =============================================================================

async def estimate_travel(
    from_lat: Optional[float], from_lon: Optional[float],
    to_lat: Optional[float],   to_lon: Optional[float],
    mode: Mode,
) -> TravelEstimate:
    """Distance (and, for road modes, driving time) between two coordinates."""
    if None in (from_lat, from_lon, to_lat, to_lon):
        raise MissingCoordinatesError(
            "Both endpoints need latitude and longitude before a distance can be estimated."
        )

    if mode in _AIR_MODES:
        return TravelEstimate(haversine_km(from_lat, from_lon, to_lat, to_lon), STRATEGY_HAVERSINE)

    if mode in _ROAD_MODES:
        return await road_travel(from_lat, from_lon, to_lat, to_lon)

    factor = _WALK_DETOUR_FACTOR if mode == AccessType.WALK else _RAIL_DETOUR_FACTOR
    return TravelEstimate(
        round(haversine_km(from_lat, from_lon, to_lat, to_lon) * factor, 2),
        STRATEGY_DETOUR,
    )


async def estimate_distance(
    from_lat: float, from_lon: float,
    to_lat: float,   to_lon: float,
    mode: Mode,
) -> float:
    """Backwards-compatible helper returning only the distance in km."""
    return (await estimate_travel(from_lat, from_lon, to_lat, to_lon, mode)).distance_km
