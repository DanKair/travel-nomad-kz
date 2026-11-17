"""
Authentication Dependencies
- API Key verification for mutations
- Admin user authentication for SQLAdmin
"""

from fastapi.security import APIKeyHeader
import secrets
from fastapi import HTTPException, status, Depends, Request
from app.core.config import settings

# This adds the "Authorize" button in Swagger UI
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(api_key: str = Depends(api_key_header)):
    """
    Dependency to require a valid API Key for mutating operations.
    If 'api_key' is missing (from Swagger or request), it raises 403.
    """
    # Compare as bytes: compare_digest raises TypeError on non-ASCII str input,
    # which would turn a bad key into a 500 instead of a 403.
    if not api_key or not secrets.compare_digest(
        api_key.encode("utf-8"), settings.TEAM_API_KEY.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key

import logging

logger = logging.getLogger(__name__)

def get_client_ip(request: Request) -> str:
    """
    Resolve the real client IP.

    X-Forwarded-For is "client, proxy1, proxy2": each proxy APPENDS the address
    it saw. The left-most entries are whatever the client sent, so trusting
    them lets anyone claim to be 127.0.0.1. We only trust the entry written by
    our own outermost proxy, i.e. the TRUSTED_PROXY_COUNT-th from the right.
    """
    direct_ip = request.client.host if request.client else ""
    hops = settings.TRUSTED_PROXY_COUNT
    forwarded = request.headers.get("X-Forwarded-For")
    if hops <= 0 or not forwarded:
        return direct_ip
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if len(parts) < hops:
        return direct_ip
    return parts[-hops]


def is_admin_ip(request: Request) -> bool:
    """Check if the requesting client IP is in the allowed admin list."""
    client_ip = get_client_ip(request)

    allowed = settings.ALLOWED_ADMIN_IPS

    if client_ip in allowed:
        return True

    if "localhost" in allowed and client_ip in ["127.0.0.1", "::1"]:
        return True

    logger.warning(f"Admin access DENIED for IP: {client_ip}")
    return False
