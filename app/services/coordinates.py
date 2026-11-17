"""
Geocoding — turn a place name into coordinates via OSM Nominatim.

Nominatim usage policy: max 1 request/second and a real User-Agent.
This is fine for an admin adding places by hand; it is NOT suitable for
bulk imports (supply latitude/longitude explicitly for those).
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.services.distance import get_http_client

logger = logging.getLogger(__name__)


class GeocodingUnavailable(Exception):
    """The geocoder could not be reached or returned garbage."""


async def geocode_async(name: str) -> Optional[dict]:
    """
    Returns the best Nominatim match (dict with "lat"/"lon" strings),
    or None when the place is genuinely not found.

    Raises GeocodingUnavailable on network/HTTP errors so the caller can tell
    "no such place" (client's problem) apart from "service down" (ours).
    """
    try:
        resp = await get_http_client().get(
            f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search",
            # `params` URL-encodes the name; countrycodes restricts matches to
            # Kazakhstan instead of hoping the ", Kazakhstan" suffix is enough.
            params={"q": name, "format": "json", "limit": 1, "countrycodes": "kz"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Geocoding failed for %r: %r", name, exc)
        raise GeocodingUnavailable(str(exc)) from exc

    if not data:
        return None
    return data[0]
