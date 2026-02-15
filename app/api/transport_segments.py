from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TransportSegment
from app.schemas import TransportSegmentResponse, TransportSegmentCreate, TransportSegmentUpdate

router = APIRouter(prefix="/transport-segments", tags=["Transport Segments"])

@router.get("", response_model=List[TransportSegmentResponse])
def get_transport_segments(db: Session = Depends(get_db)):
    """Get all transport segments."""
    transport_segments = db.query(TransportSegment).all()
    return transport_segments

@router.get("/{segment_id}", response_model=TransportSegmentResponse)
def get_transport_segment(segment_id: int, db: Session = Depends(get_db)):
    """Get a specific transport segment by ID."""
    transport_segment = db.query(TransportSegment).filter(TransportSegment.id == segment_id).first()
    if not transport_segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")
    return transport_segment

@router.post("", response_model=TransportSegmentResponse, status_code=201)
def create_transport_segment(segment_data: TransportSegmentCreate, db: Session = Depends(get_db)):
    """Create a new transport segment."""
    new_segment = TransportSegment(**segment_data.model_dump())
    db.add(new_segment)
    db.commit()
    db.refresh(new_segment)
    return new_segment

@router.put("/{segment_id}", response_model=TransportSegmentResponse)
def update_transport_segment(segment_id: int, segment_data: TransportSegmentUpdate, db: Session = Depends(get_db)):
    """Update an existing transport segment."""
    segment = db.query(TransportSegment).filter(TransportSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")
    
    # Update only provided fields
    update_data = segment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
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
