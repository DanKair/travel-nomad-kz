"""
Point Nodes API - CRUD endpoints for last-mile access management

PointNode connects TouristPoints to Nodes (last-mile access).
This API allows you to configure how tourists reach destinations from transportation nodes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.enums import AccessType
from app.models import PointNode, TouristPoint, Node
from app.schemas import (
    PointNodeResponse,
    PointNodeCreate,
    PointNodeEstimateRequest,
    PointNodeEstimateResponse,
    PointNodeAutoConnectRequest,
)
from app.core.auth import require_api_key
from app.services.distance import estimate_travel, haversine_km, MissingCoordinatesError
from app.services.pricing import (
    EstimatedMetrics,
    estimate_metrics,
    estimate_cost,
    estimate_time_minutes,
    estimate_co2,
    default_comfort,
)

router = APIRouter(prefix="/point-nodes", tags=["Point Nodes (Last-Mile Access)"])

_METRIC_FIELDS = ("distance_km", "time_minutes", "cost", "co2_kg", "comfort_score")

# Within this straight-line distance a node counts as "walkable" for auto-connect.
_WALKABLE_KM = 1.5

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

async def _estimate_access(point: TouristPoint, node: Node, access_type: AccessType) -> EstimatedMetrics:
    """Distance lookup node → tourist point, plus every metric derived from it."""
    try:
        travel = await estimate_travel(
            node.latitude, node.longitude, point.latitude, point.longitude, access_type
        )
    except MissingCoordinatesError:
        raise HTTPException(
            status_code=422,
            detail=f"Tourist point '{point.name}' has no coordinates. Set its latitude/longitude "
                   f"first, or supply distance_km manually."
        )
    return estimate_metrics(access_type, travel)

async def _fill_access_auto_fields(data: dict, point: TouristPoint, node: Node) -> dict:
    """Fill distance, time, cost, CO2 and comfort for a PointNode where missing."""
    access_type = data["access_type"]

    if data.get("distance_km") is None:
        estimated = await _estimate_access(point, node, access_type)
        defaults = {f: getattr(estimated, f) for f in _METRIC_FIELDS}
    else:
        distance_km = data["distance_km"]
        defaults = {
            "time_minutes": estimate_time_minutes(access_type, distance_km)[0],
            "cost": estimate_cost(access_type, distance_km),
            "co2_kg": estimate_co2(access_type, distance_km),
            "comfort_score": default_comfort(access_type),
        }

    for field in _METRIC_FIELDS:
        if data.get(field) is None:
            data[field] = defaults[field]
    return data

async def _reject_duplicate(db: AsyncSession, point_id: int, node_id: int, access_type: AccessType) -> None:
    result = await db.execute(
        select(PointNode).filter(
            PointNode.tourist_point_id == point_id,
            PointNode.node_id == node_id,
            PointNode.access_type == access_type,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=409,
            detail=f"This tourist point already has '{access_type.value}' access from that node."
        )

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/estimate",
             response_model=PointNodeEstimateResponse,
             dependencies=[Depends(require_api_key)])
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

    m = await _estimate_access(point, node, body.access_type)
    return PointNodeEstimateResponse(
        access_type=body.access_type,
        distance_km=m.distance_km,
        time_minutes=m.time_minutes,
        cost=m.cost,
        co2_kg=m.co2_kg,
        comfort_score=m.comfort_score,
        distance_strategy=m.distance_strategy,
        time_strategy=m.time_strategy,
    )

@router.post("/auto-connect",
             response_model=List[PointNodeResponse],
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def auto_connect_tourist_point(
    body: PointNodeAutoConnectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Make a tourist point routable in one call: find its nearest transport
    node(s) and create the last-mile access with estimated metrics.

    A tourist point with no PointNode cannot be reached by the router at all,
    so this is the usual next step after `POST /tourist-points`.

    Nearest = straight-line distance. That is a heuristic: a node across a
    mountain ridge can be "near" but badly connected, so review the result
    (the response shows the real road distance) and delete what does not fit.
    """
    point = await _get_tourist_point_or_404(db, body.tourist_point_id)
    if point.latitude is None or point.longitude is None:
        raise HTTPException(
            status_code=422,
            detail=f"Tourist point '{point.name}' has no coordinates to measure from."
        )

    nodes = (await db.execute(select(Node))).scalars().all()
    ranked = sorted(
        ((haversine_km(n.latitude, n.longitude, point.latitude, point.longitude), n) for n in nodes),
        key=lambda pair: pair[0],
    )
    candidates = [(d, n) for d, n in ranked if d <= body.max_radius_km]
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No transport node within {body.max_radius_km} km of '{point.name}'. "
                   f"Create a node nearby first, or raise max_radius_km."
        )

    existing = (await db.execute(
        select(PointNode).filter(PointNode.tourist_point_id == point.id)
    )).scalars().all()
    taken = {(pn.node_id, pn.access_type) for pn in existing}

    created: List[PointNode] = []
    for straight_km, node in candidates:
        if len(created) >= body.max_nodes:
            break
        access_type = body.access_type or (
            AccessType.WALK if straight_km <= _WALKABLE_KM else AccessType.TAXI
        )
        if (node.id, access_type) in taken:
            continue
        m = await _estimate_access(point, node, access_type)
        pn = PointNode(
            tourist_point_id=point.id,
            node_id=node.id,
            access_type=access_type,
            distance_km=m.distance_km,
            time_minutes=m.time_minutes,
            cost=m.cost,
            co2_kg=m.co2_kg,
            comfort_score=m.comfort_score,
            description=f"Auto-connected: {access_type.value} from {node.name} "
                        f"(distance via {m.distance_strategy}).",
        )
        db.add(pn)
        created.append(pn)

    if not created:
        raise HTTPException(
            status_code=409,
            detail="The nearest node(s) are already connected to this tourist point."
        )

    await db.commit()
    for pn in created:
        await db.refresh(pn)
    return created

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
    
    if tourist_point_id is not None:
        query = query.filter(PointNode.tourist_point_id == tourist_point_id)
    if node_id is not None:
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
    
    Metrics (distance, time, cost, CO2, comfort) are auto-calculated if omitted.
    """
    point = await _get_tourist_point_or_404(db, point_node_data.tourist_point_id)
    node = await _get_node_or_404(db, point_node_data.node_id)
    await _reject_duplicate(db, point.id, node.id, point_node_data.access_type)

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
    """
    Replace a point node. PUT is a full replacement: any metric you leave out
    is re-estimated for the (possibly new) node / point / access type, so a
    stale distance can never survive a change of endpoints.
    """
    result = await db.execute(select(PointNode).filter(PointNode.id == point_node_id))
    point_node = result.scalars().first()
    if not point_node:
        raise HTTPException(status_code=404, detail="Point node not found")

    point = await _get_tourist_point_or_404(db, point_node_data.tourist_point_id)
    node = await _get_node_or_404(db, point_node_data.node_id)

    data = await _fill_access_auto_fields(point_node_data.model_dump(), point, node)
    for field, value in data.items():
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
