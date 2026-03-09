"""
Kazakhstan Tourism Routing API - Main Application

FastAPI application entry point with all routers and lifespan events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, engine
from app.api import regions, tourist_points, routing, tourist_point_categories, point_nodes, transport_segments, nodes, data_management
from sqladmin import Admin
from app.admin.views import admin_views


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
    
    yield
    
    # Shutdown (cleanup if needed)
    print("👋 Shutting down...")


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
    debug=settings.debug,
    # Move documentation behind /api prefix for easier proxying
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# Configure CORS (for frontend integration later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers with /api prefix
app.include_router(regions.router, prefix="/api")
app.include_router(tourist_points.router, prefix="/api")
app.include_router(tourist_point_categories.router, prefix="/api")
app.include_router(routing.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")
app.include_router(transport_segments.router, prefix="/api")
app.include_router(point_nodes.router, prefix="/api")
app.include_router(data_management.router, prefix="/api")

# Setup SQLAdmin
admin = Admin(app, engine)
for view in admin_views:
    admin.add_view(view)

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
        reload=settings.debug
    )
