"""
Routing API Endpoint

Main endpoint for calculating optimal routes from nodes to tourist points.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas import RouteResponse, RouteAlternativesResponse
from app.services.routing import RoutingService, RouteNotFoundError
from fastapi_cache.decorator import cache
from app.cache import route_key_builder, ROUTES_NAMESPACE
from app.core.config import settings


router = APIRouter(prefix="/routes", tags=["Routing"])


@router.get("", response_model=RouteResponse)
@cache(expire=settings.ROUTE_CACHE_TTL_S, namespace=ROUTES_NAMESPACE, key_builder=route_key_builder)
async def calculate_route(
    from_node: str = Query(..., description="Starting node slug (e.g., 'almaty')"),
    to_tourist_point: str = Query(..., description="Destination tourist point slug (e.g., 'charyn-canyon')"),
    time_weight: Optional[float] = Query(None, ge=0, le=1, description="Time importance (0-1)"),
    cost_weight: Optional[float] = Query(None, ge=0, le=1, description="Cost importance (0-1)"),
    comfort_weight: Optional[float] = Query(None, ge=0, le=1, description="Comfort importance (0-1)"),
    co2_weight: Optional[float] = Query(None, ge=0, le=1, description="CO2 importance (0-1)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate optimal route from a node to a tourist point.
    
    This endpoint:
    1. Resolves the starting node and destination tourist point
    2. Finds all possible access points (PointNodes) to the tourist point
    3. Calculates routes using multi-criteria Dijkstra algorithm
    4. Selects the best route based on weighted criteria
    5. Returns the route with last-mile access information
    
    Multi-Criteria Optimization:
    - The algorithm balances time, cost, comfort, and CO2 emissions
    - Default weights can be customized via query parameters
    - Supply any subset of weights; omitted ones count as 0 and the rest are
      rescaled to sum to 1.0 (so `time_weight=0.6&cost_weight=0.4` just works)
    
    Args:
        from_node: Starting node slug (e.g., "almaty")
        to_tourist_point: Destination tourist point slug (e.g., "charyn-canyon")
        time_weight: Optional custom weight for time (default from config)
        cost_weight: Optional custom weight for cost (default from config)
        comfort_weight: Optional custom weight for comfort (default from config)
        co2_weight: Optional custom weight for CO2 (default from config)
    
    Returns:
        RouteResponse with:
        - Complete route steps (transport segments)
        - Last-mile access information
        - Total metrics (distance, time, cost, CO2)
        - Optimization score
    
    Raises:
        400: If invalid weights provided
        404: If starting node or tourist point not found
        404: If no valid route exists
    
    Example:
        GET /routes?from_node=almaty&to_tourist_point=charyn-canyon
        GET /routes?from_node=almaty&to_tourist_point=mausoleum-yasawi&time_weight=0.6&cost_weight=0.4
    """
    try:
        # Create routing service
        routing_service = RoutingService(db)
        
        # Calculate route
        route = await routing_service.calculate_route(
            from_node_slug=from_node,
            to_tourist_point_slug=to_tourist_point,
            time_weight=time_weight,
            cost_weight=cost_weight,
            comfort_weight=comfort_weight,
            co2_weight=co2_weight
        )
        
        return route
    
    except RouteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except ValueError as e:
        # Invalid weights
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Anything else propagates to the global handler, which logs the traceback
    # and returns a generic 500 — exception text is not echoed to clients.


@router.get("/alternatives", response_model=RouteAlternativesResponse)
@cache(expire=settings.ROUTE_CACHE_TTL_S, namespace=ROUTES_NAMESPACE, key_builder=route_key_builder)
async def calculate_route_alternatives(
    from_node: str = Query(..., description="Starting node slug (e.g., 'almaty')"),
    to_tourist_point: str = Query(..., description="Destination tourist point slug"),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate all route profile alternatives in a single request — Rome2Rio style.

    Runs 5 Dijkstra profiles simultaneously (sharing one graph build) and
    returns ALL unique route alternatives, deduplicated and labelled:
      - Optimal  (balanced: time 45%, cost 35%, comfort 10%, CO2 10%)
      - Fastest  (time 85%)
      - Cheapest (cost 85%)
      - Comfort  (comfort 80%)
      - Eco      (CO2 80%)

    When two profiles produce identical itineraries, they are merged into one
    entry with extra tags (e.g. "Also Cheapest") instead of being duplicated.

    Example:
        GET /routes/alternatives?from_node=almaty&to_tourist_point=charyn-canyon
    """
    try:
        routing_service = RoutingService(db)
        alternatives = await routing_service.calculate_all_alternatives(
            from_node_slug=from_node,
            to_tourist_point_slug=to_tourist_point,
        )
        return alternatives

    except RouteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except ValueError as e:
        # Invalid weights
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Anything else propagates to the global handler, which logs the traceback
    # and returns a generic 500 — exception text is not echoed to clients.
