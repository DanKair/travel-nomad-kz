"""
Kazakhstan Tourism Routing API - Main Application

FastAPI application entry point with all routers and lifespan events.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from app.redis import get_redis_client, close_redis
from app.core.config import settings
from app.core.database import init_db, engine
from app.api import regions, tourist_points, routing, tourist_point_categories, point_nodes, transport_segments, nodes
from sqladmin import Admin
from app.admin.views import admin_views
from app.admin.auth import admin_auth

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - On startup: Initialize database (create tables)
    - On shutdown: Cleanup (if needed)
    """
    # Startup: Initialize database
    print("🚀 Starting Kazakhstan Tourism Routing API...")
    await init_db()
    print("✅ Database initialized")
    
    # Initialize Redis Cache
    redis_client = get_redis_client()
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    print("✅ Redis Caching initialized")

    yield
    
    # Shutdown (cleanup if needed)
    print("👋 Shutting down...")
    await close_redis()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Multi-criteria routing API for tourism in Southern Kazakhstan.
    
    ## Features
    
    * **Regions**: Manage administrative regions
    * **Tourist Points**: Manage tourist destinations with filtering
    * **Routing**: Calculate optimal routes using multi-criteria Dijkstra algorithm
    * **Transport Segments**: CRUD operations for transport network management
    * **Point Nodes**: CRUD operations for last-mile access configuration
    
    ## Routing Algorithm
    
    The routing endpoint uses a multi-criteria Dijkstra algorithm with Pareto weights to balance:
    - ⏱️ Time (travel duration)
    - 💰 Cost (price in KZT)
    - 🛋️ Comfort (experience quality)
    - 🌱 CO2 (environmental impact)
    
    ## Architecture
    
    - **Node + TransportSegment**: Routing graph (used by algorithm)
    - **TouristPoint**: Content (not part of routing)
    - **PointNode**: Last-mile access (applied after routing)
    """,
    lifespan=lifespan,
    debug=settings.DEBUG,
    # Move documentation behind /api prefix for easier proxying
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# Configure CORS (for frontend integration later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,  # Set True only if using session cookies
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Sesion management for Admin Panel
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Register routers with /api prefix
app.include_router(regions.router, prefix="/api")
app.include_router(tourist_points.router, prefix="/api")
app.include_router(tourist_point_categories.router, prefix="/api")
app.include_router(routing.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")
app.include_router(transport_segments.router, prefix="/api")
app.include_router(point_nodes.router, prefix="/api")

# Setup SQLAdmin (Toggleable)
if settings.ENABLE_ADMIN:
    admin = Admin(app, engine, authentication_backend=admin_auth)
    for view in admin_views:
        admin.add_view(view)
    print("✅ SQLAdmin Panel enabled at /admin")
else:
    print("🔒 SQLAdmin Panel is disabled")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a structured 500 response without leaking internals."""
    logger.exception(f"Unhandled error on {request.method} {request.url}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred."}
    )

@app.get("/", tags=["Health"])
def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        Service health status
    """
    return {"status": "healthy", "service": settings.app_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
