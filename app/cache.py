"""
Route response cache helpers.

WHY A CUSTOM KEY BUILDER?
fastapi-cache's default key is a hash of the endpoint's *keyword arguments*.
Our endpoints receive `db: AsyncSession` via Depends, and a session's repr is
"<AsyncSession object at 0x7f...>" — a different memory address on every
request. So every request produced a brand-new key: the cache never returned a
hit, yet still wrote a dead entry to Redis each time.

The key must be built only from what actually determines the answer:
the URL path and the query parameters.

WHY INVALIDATION?
A cached route is a snapshot of the graph. The moment an admin edits a
segment, price or access point, every cached route may be wrong, so all
successful writes clear the whole "routes" namespace. Clearing everything is
crude but correct, and writes are rare compared to reads.
"""

import hashlib
import logging
from typing import Any, Callable, Optional

from fastapi_cache import FastAPICache
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

ROUTES_NAMESPACE = "routes"


def route_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: tuple,
    kwargs: dict,
) -> str:
    if request is not None:
        # Sorted so ?a=1&b=2 and ?b=2&a=1 share one entry.
        query = "&".join(f"{k}={v}" for k, v in sorted(request.query_params.multi_items()))
        raw = f"{request.url.path}?{query}"
    else:
        raw = f"{func.__module__}:{func.__name__}"
    return f"{namespace}:{hashlib.md5(raw.encode()).hexdigest()}"  # noqa: S324 (not security)


async def invalidate_route_cache() -> None:
    """Drop every cached route. Never raises: a cache problem must not fail a write."""
    try:
        await FastAPICache.clear(namespace=ROUTES_NAMESPACE)
    except Exception:
        logger.warning("Could not clear route cache", exc_info=True)
