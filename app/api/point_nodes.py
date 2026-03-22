"""
Point Nodes API - CRUD endpoints for last-mile access management

PointNode connects TouristPoints to Nodes (last-mile access).
This API allows you to configure how tourists reach destinations from transportation nodes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.constants import CO2_PER_KM_ACCESS, COMFORT_SCORE_ACCESS
from app.core.database import get_db
from app.models import PointNode, TouristPoint, Node
from app.schemas import (
    PointNodeResponse, 
    PointNodeCreate, 
    PointNodeEstimateRequest, 
    PointNodeEstimateResponse
)
from app.core.auth import require_api_key
from app.services.distance import estimate_distance

router = APIRouter(prefix="/point-nodes", tags=["Point Nodes (Last-Mile Access)"])

# =============================================================================
# HELPERS
# =============================================================================

async def _get_tourist_point_or_404(db: AsyncSession, point_id: int) -> TouristPoint:
    result = await db.execute(select(TouristPoint).filter(TouristPoint.id == point_id))
    point = result.scalars().first()
    if not point:
        raise HTTPException(status_code=404, detail=f"Tourist point (id={point_id}) not found")
    return point

async def _get_node_or_404(db: AsyncSession, node_id: int) -> Node:
    result = await db.execute(select(Node).filter(Node.id == node_id))
    node = result.scalars().first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node (id={node_id}) not found")
    return node

async def _fill_access_auto_fields(data: dict, point: TouristPoint, node: Node) -> dict:
    """
    Auto-calculate distance, time, CO2, and comfort for PointNode if missing.
    """
    access_type = data.get("access_type")
    
    # Calculate distance if missing
    if data.get("distance_km") is None:
        data["distance_km"] = await estimate_distance(
            from_lat=node.latitude,  from_lon=node.longitude,
            to_lat=point.latitude,   to_lon=point.longitude,
            mode=access_type
        )
        
    distance_km = data["distance_km"]
    
    # Calculate time if missing
    if data.get("time_minutes") is None:
        speed_map = {"walk": 5.0, "taxi": 30.0, "bus": 25.0, "shuttle": 25.0, "car": 30.0}
        speed = speed_map.get(access_type.value, 20.0)
        time_mins = int((distance_km / speed) * 60) if speed > 0 else 0
        data["time_minutes"] = max(1, time_mins) if distance_km > 0 else 0
        
    # Calculate CO2 if missing
    if data.get("co2_kg") is None:
        data["co2_kg"] = round(CO2_PER_KM_ACCESS[access_type] * distance_km, 3)
        
    # Calculate comfort if missing
    if data.get("comfort_score") is None:
        data["comfort_score"] = COMFORT_SCORE_ACCESS[access_type]
        
    return data

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/estimate", response_model=PointNodeEstimateResponse)
async def estimate_point_node(
    body: PointNodeEstimateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    **Dry-run preview** — estimate all last-mile access fields for a point node
    without saving anything to the database.
    """
    point = await _get_tourist_point_or_404(db, body.tourist_point_id)
    node = await _get_node_or_404(db, body.node_id)
    
    # Coordinates for estimation
    # TouristPoint uses its own lat/lon
    # Node uses its own lat/lon
    
    distance_km = await estimate_distance(
        from_lat=node.latitude,  from_lon=node.longitude,
        to_lat=point.latitude,   to_lon=point.longitude,
        mode=body.access_type
    )
    
    # Speed estimation: rough average for access types (km/h)
    speed_map = {
        "walk": 5.0,
        "taxi": 30.0,
        "bus": 25.0,
        "shuttle": 25.0,
        "car": 30.0
    }
    speed = speed_map.get(body.access_type.value, 20.0)
    time_minutes = int((distance_km / speed) * 60) if speed > 0 else 0
    if time_minutes == 0 and distance_km > 0:
        time_minutes = 1 # Minimum 1 minute if there is distance
        
    return PointNodeEstimateResponse(
        access_type=body.access_type,
        distance_km=distance_km,
        time_minutes=max(1, time_minutes),
        co2_kg=round(CO2_PER_KM_ACCESS[body.access_type] * distance_km, 3),
        comfort_score=COMFORT_SCORE_ACCESS[body.access_type],
        distance_strategy="osrm" if body.access_type != "walk" else "haversine"
    )

@router.get("", response_model=List[PointNodeResponse])
async def get_point_nodes(
    tourist_point_id: int | None = None,
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all point nodes (last-mile access configurations).
    
    Optional filters:
    - tourist_point_id: Filter by specific tourist point
    - node_id: Filter by specific node
    """
    query = select(PointNode)
    
    if tourist_point_id:
        query = query.filter(PointNode.tourist_point_id == tourist_point_id)
    if node_id:
        query = query.filter(PointNode.node_id == node_id)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{point_node_id}", response_model=PointNodeResponse)
async def get_point_node(point_node_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific point node by ID."""
    result = await db.execute(select(PointNode).filter(PointNode.id == point_node_id))
    point_node = result.scalars().first()
    if not point_node:
        raise HTTPException(status_code=404, detail="Point node not found")
    return point_node

@router.post("", 
             response_model=PointNodeResponse, 
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def create_point_node(point_node_data: PointNodeCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new point node (last-mile access).
    
    Metrics (distance, time, CO2, comfort) are auto-calculated if omitted.
    """
    point = await _get_tourist_point_or_404(db, point_node_data.tourist_point_id)
    node = await _get_node_or_404(db, point_node_data.node_id)
    
    data = point_node_data.model_dump()
    data = await _fill_access_auto_fields(data, point, node)
    
    new_point_node = PointNode(**data)
    db.add(new_point_node)
    await db.commit()
    await db.refresh(new_point_node)
    return new_point_node

@router.put("/{point_node_id}", 
            response_model=PointNodeResponse,
            dependencies=[Depends(require_api_key)])
async def update_point_node(
    point_node_id: int, 
    point_node_data: PointNodeCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Update an existing point node (recalculates missing metrics if access_type changes)."""
    result = await db.execute(select(PointNode).filter(PointNode.id == point_node_id))
    point_node = result.scalars().first()
    if not point_node:
        raise HTTPException(status_code=404, detail="Point node not found")
    
    # Logic similar to transport segment updates
    update_data = point_node_data.model_dump(exclude_unset=True)
    
    # If access_type or distance changes, we should ideally re-fill other fields if they are missing
    # But for now, just apply the provided data
    for field, value in update_data.items():
        setattr(point_node, field, value)
    
    await db.commit()
    await db.refresh(point_node)
    return point_node

@router.delete("/{point_node_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_api_key)])
async def delete_point_node(point_node_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a point node."""
    result = await db.execute(select(PointNode).filter(PointNode.id == point_node_id))
    point_node = result.scalars().first()
    if not point_node:
        raise HTTPException(status_code=404, detail="Point node not found")
    
    await db.delete(point_node)
    await db.commit()
    return None
