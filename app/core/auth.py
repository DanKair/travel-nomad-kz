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
    if not api_key or not secrets.compare_digest(api_key, settings.TEAM_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key

import logging

logger = logging.getLogger(__name__)

def is_admin_ip(request: Request) -> bool:
    """Check if the requesting client IP is in the allowed admin list."""
    # Handle proxy headers (X-Forwarded-For) if they exist
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host
        
    allowed = settings.ALLOWED_ADMIN_IPS
    
    # Debug log for Docker IP verification
    logger.info(f"Checking admin access for IP: {client_ip} (Allowed: {allowed})")
    
    if client_ip in allowed:
        logger.info(f"Access GRANTED for IP: {client_ip}")
        return True
    
    if "localhost" in allowed and client_ip in ["127.0.0.1", "::1"]:
        logger.info(f"Access GRANTED (Localhost) for IP: {client_ip}")
        return True
        
    logger.warning(f"Access DENIED for IP: {client_ip}")
    return False
