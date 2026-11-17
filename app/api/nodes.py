"""
Nodes API - CRUD endpoints for transportation node management

A Node is a physical location in the routing graph (city, station, stop, etc.)
Supports filtering by node_type and name search to avoid having to memorize IDs.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select

from app.core.database import get_db
from app.enums import NodeType
from app.models import Node, TransportSegment, PointNode
from app.schemas import NodeResponse, NodeCreate, NodeUpdate
from app.core.auth import require_api_key
from app.services.coordinates import geocode_async, GeocodingUnavailable

router = APIRouter(prefix="/transport-nodes", tags=["Transport Nodes"])


@router.get("", response_model=List[NodeResponse])
async def get_transport_nodes(
    node_type: Optional[NodeType] = Query(
        None,
        description="Filter by node type (city, airport, train_station, bus_station, bus_stop, transport_stop, village)"
    ),
    name: Optional[str] = Query(
        None,
        description="Search nodes by name (case-insensitive partial match). E.g. 'alma' matches 'Almaty'"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all transportation nodes with optional filtering.

    Filters:
    - **node_type**: Exact match on node type enum (e.g. 'city', 'airport')
    - **name**: Case-insensitive partial search on node name (e.g. 'alm' → Almaty)

    Example: GET /transport-nodes?node_type=city&name=alm
    """
    query = select(Node)

    # Filter: exact enum match on node_type
    if node_type:
        query = query.filter(Node.node_type == node_type)

    # Filter: partial, case-insensitive search on name
    if name:
        query = query.filter(Node.name.ilike(f"%{name}%"))

    query = query.order_by(Node.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node_by_id(node_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific node by its ID."""
    result = await db.execute(select(Node).filter(Node.id == node_id))
    node = result.scalars().first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node



@router.post("",
             response_model=NodeResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def create_node(node_data: NodeCreate, db: AsyncSession = Depends(get_db)):
    # Creates slug if slug field isn't provided
    if not node_data.slug:
        node_data.slug = slugify(node_data.name)

    result = await db.execute(select(Node).filter(Node.slug == node_data.slug))
    exists = result.scalars().first()
    if exists:
        raise HTTPException(409, "Node exists")

    # Geocode when EITHER coordinate is missing. (`not latitude` would also
    # treat a legitimate 0.0 as missing, and `and` let a half-filled pair through.)
    if node_data.latitude is None or node_data.longitude is None:
        try:
            geo = await geocode_async(node_data.name)
        except GeocodingUnavailable:
            raise HTTPException(
                status_code=503,
                detail="Geocoding service is unavailable. Retry later or supply "
                       "latitude and longitude explicitly."
            )
        if not geo:
            raise HTTPException(
                status_code=422,
                detail=f"Could not find coordinates for '{node_data.name}'. "
                       f"Supply latitude and longitude explicitly."
            )

        node_data.latitude = float(geo["lat"])
        node_data.longitude = float(geo["lon"])

    new_node = Node(**node_data.model_dump())
    db.add(new_node)
    await db.commit()
    await db.refresh(new_node)
    return new_node

@router.patch("/{node_id}",
              response_model=NodeResponse,
              dependencies=[Depends(require_api_key)])
async def update_node(node_id: int, node_data: NodeUpdate, db: AsyncSession = Depends(get_db)):
    """Partially update a node (only provided fields are changed)."""
    result = await db.execute(select(Node).filter(Node.id == node_id))
    node = result.scalars().first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    for key, value in node_data.model_dump(exclude_unset=True).items():
        if value is None:
            continue  # every Node column is NOT NULL: null means "leave as is"
        setattr(node, key, value)

    await db.commit()
    await db.refresh(node)
    return node


@router.delete("/{node_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_api_key)])
async def delete_node(node_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a node by its ID."""
    result = await db.execute(select(Node).filter(Node.id == node_id))
    node = result.scalars().first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # A node that is still part of the graph must not vanish silently: that
    # would cut routes. Make the admin remove its connections deliberately.
    segments = (await db.execute(
        select(func.count()).select_from(TransportSegment).filter(
            (TransportSegment.from_node_id == node_id) | (TransportSegment.to_node_id == node_id)
        )
    )).scalar_one()
    access_points = (await db.execute(
        select(func.count()).select_from(PointNode).filter(PointNode.node_id == node_id)
    )).scalar_one()
    if segments or access_points:
        raise HTTPException(
            status_code=409,
            detail=f"Node is still used by {segments} transport segment(s) and "
                   f"{access_points} point node(s). Delete those first."
        )

    await db.delete(node)
    await db.commit()
    return None


