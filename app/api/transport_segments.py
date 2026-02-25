"""
Transport Segments API - CRUD + Distance / Time Estimation

A TransportSegment is a directed edge in the routing graph — it connects
two Nodes with a specific transport mode and cost metrics.

AUTO-CALCULATION (all 4 fields are optional on create):
    distance_km   → Haversine (air/cable), OSRM (roads), Haversine×1.2 (train)
    time_minutes  → distance_km / SPEED_KMH[mode] × 60
    co2_kg        → CO2_PER_KM[mode] × distance_km
    comfort_score → COMFORT_SCORE[mode]

ESTIMATE ENDPOINT:
    POST /transport-segments/estimate
    Dry-run preview — returns all 4 calculated values without saving anything.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased

from app.constants import CO2_PER_KM, COMFORT_SCORE, SPEED_KMH
from app.database import get_db
from app.enums import TransportMode
from app.models import TransportSegment, Node
from app.schemas import (
    TransportSegmentResponse,
    TransportSegmentCreate,
    TransportSegmentUpdate,
    SegmentEstimateRequest,
    SegmentEstimateResponse,
)
from app.services.distance import estimate_segment

router = APIRouter(prefix="/transport-segments", tags=["Transport Segments"])


# =============================================================================
# HELPERS
# =============================================================================

def _get_node_or_404(db: Session, node_id: int, label: str) -> Node:
    """Fetch a Node by ID, raise 404 with a helpful message if not found."""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{label} (id={node_id}) not found. "
                f"Use GET /transport-nodes?name=... to find valid IDs."
            )
        )
    return node


def _fill_auto_fields(data: dict, mode: TransportMode, distance_km: float) -> dict:
    """
    Fill co2_kg and comfort_score when not provided.
    distance_km must already be resolved before calling this.
    """
    if data.get("co2_kg") is None:
        data["co2_kg"] = round(CO2_PER_KM[mode] * distance_km, 3)
    if data.get("comfort_score") is None:
        data["comfort_score"] = COMFORT_SCORE[mode]
    return data


def _distance_strategy_name(mode: TransportMode) -> str:
    """Human-readable label for which distance strategy was used."""
    from app.services.distance import _AIR_MODES, _ROAD_MODES
    if mode in _AIR_MODES:
        return "haversine"
    if mode in _ROAD_MODES:
        return "osrm"
    return "haversine_x_detour"


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/estimate", response_model=SegmentEstimateResponse)
async def estimate_transport_segment(
    body: SegmentEstimateRequest,
    db: Session = Depends(get_db)
):
    """
    **Dry-run preview** — estimate all auto-calculated fields for a segment
    without saving anything to the database.

    Use this to verify values before calling `POST /transport-segments`.

    Returns:
    - `distance_km` — calculated from node coordinates
    - `time_minutes` — derived from distance ÷ mode speed
    - `co2_kg` — CO2_PER_KM[mode] × distance_km
    - `comfort_score` — from COMFORT_SCORE[mode]
    - `speed_kmh` — the speed constant used
    - `distance_strategy` — which algorithm calculated the distance
    """
    from_node = _get_node_or_404(db, body.from_node_id, "from_node_id")
    to_node   = _get_node_or_404(db, body.to_node_id,   "to_node_id")

    # Estimate distance + time
    estimated = await estimate_segment(
        from_lat=from_node.latitude,  from_lon=from_node.longitude,
        to_lat=to_node.latitude,      to_lon=to_node.longitude,
        mode=body.transport_mode,
    )

    distance_km = estimated["distance_km"]

    return SegmentEstimateResponse(
        transport_mode=body.transport_mode,
        distance_km=distance_km,
        time_minutes=estimated["time_minutes"],
        co2_kg=round(CO2_PER_KM[body.transport_mode] * distance_km, 3),
        comfort_score=COMFORT_SCORE[body.transport_mode],
        speed_kmh=SPEED_KMH[body.transport_mode],
        distance_strategy=_distance_strategy_name(body.transport_mode),
    )


@router.get("", response_model=List[TransportSegmentResponse])
def get_transport_segments(
    transport_mode: Optional[TransportMode] = Query(
        None,
        description="Filter by transport mode (plane, train, bus, taxi, marshrutka, car, cable_car)"
    ),
    from_node_id: Optional[int] = Query(None, description="Filter by origin node ID"),
    to_node_id:   Optional[int] = Query(None, description="Filter by destination node ID"),
    from_node_name: Optional[str] = Query(
        None, description="Partial origin name search (case-insensitive). E.g. 'alma' → Almaty"
    ),
    to_node_name: Optional[str] = Query(
        None, description="Partial destination name search. E.g. 'shym' → Shymkent"
    ),
    db: Session = Depends(get_db)
):
    """
    List all transport segments with optional filtering.

    Examples:
    - `GET /transport-segments?transport_mode=bus`
    - `GET /transport-segments?from_node_name=almaty&to_node_name=shym`
    """
    query = db.query(TransportSegment)

    if transport_mode:
        query = query.filter(TransportSegment.transport_mode == transport_mode)
    if from_node_id is not None:
        query = query.filter(TransportSegment.from_node_id == from_node_id)
    if to_node_id is not None:
        query = query.filter(TransportSegment.to_node_id == to_node_id)
    if from_node_name:
        query = query.join(Node, TransportSegment.from_node_id == Node.id)
        query = query.filter(Node.name.ilike(f"%{from_node_name}%"))
    if to_node_name:
        DestNode = aliased(Node, name="dest_node")
        query = query.join(DestNode, TransportSegment.to_node_id == DestNode.id)
        query = query.filter(DestNode.name.ilike(f"%{to_node_name}%"))

    return query.all()


@router.get("/{segment_id}", response_model=TransportSegmentResponse)
def get_transport_segment(segment_id: int, db: Session = Depends(get_db)):
    """Get a specific transport segment by ID."""
    segment = db.query(TransportSegment).filter(TransportSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")
    return segment


@router.post("", response_model=TransportSegmentResponse, status_code=201)
async def create_transport_segment(
    segment_data: TransportSegmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new transport segment.

    All four metric fields are **optional** — if omitted, they are auto-calculated:
    - `distance_km` → from node coordinates (Haversine / OSRM / rail detour)
    - `time_minutes` → `distance_km / SPEED_KMH[mode] × 60`
    - `co2_kg` → `CO2_PER_KM[mode] × distance_km`
    - `comfort_score` → `COMFORT_SCORE[mode]`

    Use `POST /transport-segments/estimate` to preview values first.
    """
    from_node = _get_node_or_404(db, segment_data.from_node_id, "from_node_id")
    to_node   = _get_node_or_404(db, segment_data.to_node_id,   "to_node_id")

    data = segment_data.model_dump()
    mode = segment_data.transport_mode

    # Auto-calculate distance + time if not supplied
    if data.get("distance_km") is None or data.get("time_minutes") is None:
        estimated = await estimate_segment(
            from_lat=from_node.latitude,  from_lon=from_node.longitude,
            to_lat=to_node.latitude,      to_lon=to_node.longitude,
            mode=mode,
        )
        if data.get("distance_km") is None:
            data["distance_km"] = estimated["distance_km"]
        if data.get("time_minutes") is None:
            data["time_minutes"] = estimated["time_minutes"]

    # Auto-calculate CO2 + comfort from the now-resolved distance
    data = _fill_auto_fields(data, mode, data["distance_km"])

    new_segment = TransportSegment(**data)
    db.add(new_segment)
    db.commit()
    db.refresh(new_segment)
    return new_segment


@router.put("/{segment_id}", response_model=TransportSegmentResponse)
async def update_transport_segment(
    segment_id: int,
    segment_data: TransportSegmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing transport segment (only provided fields change).

    If `transport_mode` or `distance_km` changes and `co2_kg` / `comfort_score`
    are not supplied, they are **recalculated** from the new values.
    """
    segment = db.query(TransportSegment).filter(TransportSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")

    update_data = segment_data.model_dump(exclude_unset=True)
    effective_mode     = update_data.get("transport_mode", segment.transport_mode)
    effective_distance = update_data.get("distance_km", segment.distance_km)

    # Recalculate CO2 + comfort if mode or distance changed
    if "transport_mode" in update_data or "distance_km" in update_data:
        update_data = _fill_auto_fields(update_data, effective_mode, effective_distance)

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
