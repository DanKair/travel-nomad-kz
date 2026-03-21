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
from app.models import PointNode
from app.schemas import PointNodeResponse, PointNodeCreate
from app.core.auth import require_api_key

router = APIRouter(prefix="/point-nodes", tags=["Point Nodes (Last-Mile Access)"])

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
    
    This defines how to reach a tourist point from a transportation node.
    Example: "From Turkestan city → Taxi 2.3km → Mausoleum"
    """
    new_point_node = PointNode(**point_node_data.model_dump())
    db.add(new_point_node)
    await db.commit()
    await db.refresh(new_point_node)
    return new_point_node

@router.put("/{point_node_id}", 
            response_model=PointNodeResponse,
            dependencies=[Depends(require_api_key)])
async def update_point_node(point_node_id: int, point_node_data: PointNodeCreate, db: AsyncSession = Depends(get_db)):
    """Update an existing point node."""
    result = await db.execute(select(PointNode).filter(PointNode.id == point_node_id))
    point_node = result.scalars().first()
    if not point_node:
        raise HTTPException(status_code=404, detail="Point node not found")
    
    # Update all fields (PointNodeCreate is used for both create and update)
    update_data = point_node_data.model_dump()
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
