"""
Transport Segments API - CRUD endpoints for routing graph edge management

A TransportSegment is a directed edge in the routing graph — it connects
two Nodes with a specific transport mode and cost metrics.

Supports filtering by transport_mode, from_node_id, and to_node_id so you
don't have to remember all node IDs manually.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import TransportMode
from app.models import TransportSegment, Node
from app.schemas import TransportSegmentResponse, TransportSegmentCreate, TransportSegmentUpdate

router = APIRouter(prefix="/transport-segments", tags=["Transport Segments"])


@router.get("", response_model=List[TransportSegmentResponse])
def get_transport_segments(
    transport_mode: Optional[TransportMode] = Query(
        None,
        description="Filter by transport mode (plane, train, bus, taxi, marshrutka)"
    ),
    from_node_id: Optional[int] = Query(
        None,
        description="Filter segments departing from this node ID"
    ),
    to_node_id: Optional[int] = Query(
        None,
        description="Filter segments arriving at this node ID"
    ),
    from_node_name: Optional[str] = Query(
        None,
        description="Filter by origin node name (case-insensitive partial match). E.g. 'alma' → Almaty"
    ),
    to_node_name: Optional[str] = Query(
        None,
        description="Filter by destination node name (case-insensitive partial match). E.g. 'shym' → Shymkent"
    ),
    db: Session = Depends(get_db)
):
    """
    Get all transport segments (graph edges) with optional filtering.

    Filters:
    - **transport_mode**: Exact match on mode (bus, train, plane, taxi, marshrutka)
    - **from_node_id**: Exact match on origin node ID
    - **to_node_id**: Exact match on destination node ID
    - **from_node_name**: Partial name search on origin node (no ID memorisation needed)
    - **to_node_name**: Partial name search on destination node (no ID memorisation needed)

    Examples:
    - All bus segments: `GET /transport-segments?transport_mode=bus`
    - All segments from Almaty: `GET /transport-segments?from_node_name=almaty`
    - Almaty → Shymkent by any mode: `GET /transport-segments?from_node_name=almaty&to_node_name=shym`
    """
    # Use aliases so we can join Node twice (once for origin, once for destination)
    FromNode = db.query(Node).subquery()  # We'll do proper aliasing below

    # Build the base query
    query = db.query(TransportSegment)

    # Simple ID / enum filters
    if transport_mode:
        query = query.filter(TransportSegment.transport_mode == transport_mode)

    if from_node_id is not None:
        query = query.filter(TransportSegment.from_node_id == from_node_id)

    if to_node_id is not None:
        query = query.filter(TransportSegment.to_node_id == to_node_id)

    # Name-based filters: join Node for origin and/or destination
    if from_node_name:
        # Join the Node table for the origin node and filter by name
        query = query.join(
            Node,
            TransportSegment.from_node_id == Node.id,
            isouter=False,
            # Give this join an alias so it doesn't conflict with to_node join
        ).filter(Node.name.ilike(f"%{from_node_name}%"))

    if to_node_name:
        # We need a second join to Node for the destination.
        # SQLAlchemy allows aliasing with `aliased`.
        from sqlalchemy.orm import aliased
        DestNode = aliased(Node, name="dest_node")
        query = query.join(
            DestNode,
            TransportSegment.to_node_id == DestNode.id,
            isouter=False
        ).filter(DestNode.name.ilike(f"%{to_node_name}%"))

    return query.all()


@router.get("/{segment_id}", response_model=TransportSegmentResponse)
def get_transport_segment(segment_id: int, db: Session = Depends(get_db)):
    """Get a specific transport segment by ID."""
    segment = db.query(TransportSegment).filter(TransportSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")
    return segment


@router.post("", response_model=TransportSegmentResponse, status_code=201)
def create_transport_segment(segment_data: TransportSegmentCreate, db: Session = Depends(get_db)):
    """
    Create a new transport segment (graph edge).

    Both from_node_id and to_node_id must reference existing nodes.
    Use GET /transport-nodes to discover node IDs, or filter by name.
    """
    # Validate that referenced nodes exist
    if not db.query(Node).filter(Node.id == segment_data.from_node_id).first():
        raise HTTPException(status_code=404, detail=f"from_node_id={segment_data.from_node_id} not found")
    if not db.query(Node).filter(Node.id == segment_data.to_node_id).first():
        raise HTTPException(status_code=404, detail=f"to_node_id={segment_data.to_node_id} not found")

    new_segment = TransportSegment(**segment_data.model_dump())
    db.add(new_segment)
    db.commit()
    db.refresh(new_segment)
    return new_segment


@router.put("/{segment_id}", response_model=TransportSegmentResponse)
def update_transport_segment(segment_id: int, segment_data: TransportSegmentUpdate, db: Session = Depends(get_db)):
    """Update an existing transport segment (only provided fields are changed)."""
    segment = db.query(TransportSegment).filter(TransportSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")

    for field, value in segment_data.model_dump(exclude_unset=True).items():
        setattr(segment, field, value)

    db.commit()
    db.refresh(segment)
    return segment


@router.delete("/{segment_id}", status_code=204)
def delete_transport_segment(segment_id: int, db: Session = Depends(get_db)):
    """Delete a transport segment."""
    segment = db.query(TransportSegment).filter(TransportSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")

    db.delete(segment)
    db.commit()
    return None
