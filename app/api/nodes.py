"""
Nodes API - CRUD endpoints for transportation node management

A Node is a physical location in the routing graph (city, station, stop, etc.)
Supports filtering by node_type and name search to avoid having to memorize IDs.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import NodeType
from app.models import Node
from app.schemas import NodeResponse, NodeCreate, NodeUpdate

router = APIRouter(prefix="/transport-nodes", tags=["Transport Nodes"])


@router.get("", response_model=List[NodeResponse])
def get_transport_nodes(
    node_type: Optional[NodeType] = Query(
        None,
        description="Filter by node type (city, airport, train_station, bus_station, bus_stop, transport_stop, village)"
    ),
    name: Optional[str] = Query(
        None,
        description="Search nodes by name (case-insensitive partial match). E.g. 'alma' matches 'Almaty'"
    ),
    db: Session = Depends(get_db)
):
    """
    Get all transportation nodes with optional filtering.

    Filters:
    - **node_type**: Exact match on node type enum (e.g. 'city', 'airport')
    - **name**: Case-insensitive partial search on node name (e.g. 'alm' → Almaty)

    Example: GET /transport-nodes?node_type=city&name=alm
    """
    query = db.query(Node)

    # Filter: exact enum match on node_type
    if node_type:
        query = query.filter(Node.node_type == node_type)

    # Filter: partial, case-insensitive search on name
    if name:
        query = query.filter(Node.name.ilike(f"%{name}%"))

    return query.order_by(Node.name).all()


@router.get("/{node_id}", response_model=NodeResponse)
def get_node_by_id(node_id: int, db: Session = Depends(get_db)):
    """Get a specific node by its ID."""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.post("", response_model=NodeResponse, status_code=201)
def create_transport_node(node_data: NodeCreate, db: Session = Depends(get_db)):
    """
    Create a new transportation node.

    A node is a graph vertex — a physical location where transport can be boarded/exited.
    """
    # Prevent duplicate nodes by name
    existing = db.query(Node).filter(Node.name == node_data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Node '{node_data.name}' already exists (id={existing.id})")

    new_node = Node(**node_data.model_dump())
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node


@router.patch("/{node_id}", response_model=NodeResponse)
def update_node_data(node_id: int, node_data: NodeUpdate, db: Session = Depends(get_db)):
    """Partially update a node (only provided fields are changed)."""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    for key, value in node_data.model_dump(exclude_unset=True).items():
        setattr(node, key, value)

    db.commit()
    db.refresh(node)
    return node


@router.delete("/{node_id}", status_code=204)
def delete_node_by_id(node_id: int, db: Session = Depends(get_db)):
    """Delete a node by its ID."""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()
    return None
