"""
Nodes API - CRUD endpoints for transportation node management

A Node is a physical location in the routing graph (city, station, stop, etc.)
Supports filtering by node_type and name search to avoid having to memorize IDs.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.params import Depends

from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.enums import NodeType
from app.models import Node
from app.schemas import NodeResponse, NodeCreate, NodeUpdate
from app.core.auth import require_api_key
from app.services.coordinates import geocode_async

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

    # async geocoding
    if not node_data.latitude and not node_data.longitude:
        geo = await geocode_async(node_data.name)
        if not geo:
            raise HTTPException(404, f"Target location: {node_data.name} not found")

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
    await db.delete(node)
    await db.commit()
    return None


