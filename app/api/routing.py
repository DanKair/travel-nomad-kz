"""
Routing API Endpoint

Main endpoint for calculating optimal routes from nodes to tourist points.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import RouteResponse
from app.services.routing import RoutingService


router = APIRouter(prefix="/routes", tags=["Routing"])


@router.get("", response_model=RouteResponse)
async def calculate_route(
    from_node: str = Query(..., description="Starting node slug (e.g., 'almaty')"),
    to_tourist_point: str = Query(..., description="Destination tourist point slug (e.g., 'charyn-canyon')"),
    time_weight: Optional[float] = Query(None, ge=0, le=1, description="Time importance (0-1)"),
    cost_weight: Optional[float] = Query(None, ge=0, le=1, description="Cost importance (0-1)"),
    comfort_weight: Optional[float] = Query(None, ge=0, le=1, description="Comfort importance (0-1)"),
    co2_weight: Optional[float] = Query(None, ge=0, le=1, description="CO2 importance (0-1)"),
    db: AsyncSession = Depends(get_db)
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
    - Weights should sum to 1.0 (validated by routing service)
    
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
    
    except ValueError as e:
        # Handle validation errors (nodes not found, invalid weights, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate route: {str(e)}"
        )
