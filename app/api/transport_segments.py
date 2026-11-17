"""
Transport Segments API - CRUD + automatic distance / time / price estimation

A TransportSegment is a directed edge in the routing graph — it connects
two Nodes with a specific transport mode and cost metrics.

AUTO-CALCULATION (only the two nodes and the mode are required on create):
    distance_km   → Haversine (air/cable), OSRM (roads), Haversine×1.2 (train)
    time_minutes  → OSRM driving time × mode factor, or distance ÷ speed
    cost          → tariff model: base fare + per-km rate
    co2_kg        → CO2_PER_KM[mode] × distance_km
    comfort_score → COMFORT_SCORE[mode]
A value you supply always wins over the estimate.

    POST /transport-segments/estimate          dry-run preview, saves nothing
    GET  /transport-segments/price-check       stored prices vs. tariff model
    POST /transport-segments/{id}/recalculate  overwrite chosen fields with estimates
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.enums import TransportMode
from app.models import TransportSegment, Node
from app.schemas import (
    TransportSegmentResponse,
    TransportSegmentCreate,
    TransportSegmentUpdate,
    SegmentEstimateRequest,
    SegmentEstimateResponse,
    SegmentRecalculateRequest,
    PriceCheckItem,
    PriceCheckResponse,
)
from app.core.auth import require_api_key
from app.services.distance import estimate_travel, MissingCoordinatesError
from app.services.pricing import (
    EstimatedMetrics,
    estimate_metrics,
    estimate_cost,
    estimate_time_minutes,
    estimate_co2,
    default_comfort,
    price_deviation_pct,
)

router = APIRouter(prefix="/transport-segments", tags=["Transport Segments"])

_METRIC_FIELDS = ("distance_km", "time_minutes", "cost", "co2_kg", "comfort_score")


# =============================================================================
# HELPERS
# =============================================================================

async def _get_node_or_404(db: AsyncSession, node_id: int, label: str) -> Node:
    """Fetch a Node by ID, raise 404 with a helpful message if not found."""
    result = await db.execute(select(Node).filter(Node.id == node_id))
    node = result.scalars().first()
    if not node:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{label} (id={node_id}) not found. "
                f"Use GET /transport-nodes?name=... to find valid IDs."
            )
        )
    return node


async def _get_segment_or_404(db: AsyncSession, segment_id: int) -> TransportSegment:
    result = await db.execute(select(TransportSegment).filter(TransportSegment.id == segment_id))
    segment = result.scalars().first()
    if not segment:
        raise HTTPException(status_code=404, detail="Transport segment not found")
    return segment


def _reject_self_loop(from_node_id: int, to_node_id: int) -> None:
    if from_node_id == to_node_id:
        raise HTTPException(
            status_code=422,
            detail="from_node_id and to_node_id must be different nodes."
        )


async def _estimate_between(from_node: Node, to_node: Node, mode: TransportMode) -> EstimatedMetrics:
    """Look up the distance between two nodes and derive every metric from it."""
    try:
        travel = await estimate_travel(
            from_node.latitude, from_node.longitude,
            to_node.latitude, to_node.longitude,
            mode,
        )
    except MissingCoordinatesError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return estimate_metrics(mode, travel)


def _metrics_from_known_distance(
    mode: TransportMode, distance_km: float, driving_minutes: Optional[float] = None
) -> dict:
    """Derive time / cost / CO2 / comfort from a distance we already have."""
    minutes, _ = estimate_time_minutes(mode, distance_km, driving_minutes)
    return {
        "time_minutes": minutes,
        "cost": estimate_cost(mode, distance_km),
        "co2_kg": estimate_co2(mode, distance_km),
        "comfort_score": default_comfort(mode),
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/estimate",
             response_model=SegmentEstimateResponse,
             dependencies=[Depends(require_api_key)])
async def estimate_transport_segment(
    body: SegmentEstimateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    **Dry-run preview** — every auto-calculated field for a segment, without
    saving anything. Use it to sanity-check values before `POST /transport-segments`.

    `distance_strategy = "haversine_fallback"` means the road-routing service
    (OSRM) did not answer and the distance is a straight-line approximation.

    Requires the API key: each call may trigger an outbound request to OSRM,
    so it must not be open to anonymous callers.
    """
    _reject_self_loop(body.from_node_id, body.to_node_id)
    from_node = await _get_node_or_404(db, body.from_node_id, "from_node_id")
    to_node   = await _get_node_or_404(db, body.to_node_id,   "to_node_id")

    m = await _estimate_between(from_node, to_node, body.transport_mode)
    return SegmentEstimateResponse(
        transport_mode=body.transport_mode,
        distance_km=m.distance_km,
        time_minutes=m.time_minutes,
        cost=m.cost,
        co2_kg=m.co2_kg,
        comfort_score=m.comfort_score,
        distance_strategy=m.distance_strategy,
        time_strategy=m.time_strategy,
    )


@router.get("/price-check",
            response_model=PriceCheckResponse,
            dependencies=[Depends(require_api_key)])
async def price_check(
    threshold_pct: float = Query(
        30, ge=0, le=1000,
        description="Flag segments whose stored cost differs from the tariff model by more than this %"
    ),
    transport_mode: Optional[TransportMode] = Query(None, description="Only check this mode"),
    db: AsyncSession = Depends(get_db),
):
    """
    **Automated price check** — compare every stored segment price with what the
    tariff model predicts for its mode and distance, and list the outliers.

    This is a sanity check, not a live price feed: a flagged segment means
    "look at this one" (typo, stale fare, or a route the model fits badly),
    not "this price is wrong". Nothing is modified. To accept the model's
    value for a segment, call `POST /transport-segments/{id}/recalculate`
    with `{"fields": ["cost"]}`.

    Uses only stored data — no external calls — so it is cheap to run often.
    """
    query = select(TransportSegment).options(
        joinedload(TransportSegment.from_node), joinedload(TransportSegment.to_node)
    )
    if transport_mode:
        query = query.filter(TransportSegment.transport_mode == transport_mode)
    segments = (await db.execute(query)).scalars().all()

    flagged: List[PriceCheckItem] = []
    for seg in segments:
        estimated = estimate_cost(seg.transport_mode, seg.distance_km)
        deviation = price_deviation_pct(seg.cost, estimated)
        if deviation is None or abs(deviation) <= threshold_pct:
            continue
        flagged.append(PriceCheckItem(
            segment_id=seg.id,
            from_node=seg.from_node.name,
            to_node=seg.to_node.name,
            transport_mode=seg.transport_mode,
            distance_km=seg.distance_km,
            stored_cost=seg.cost,
            estimated_cost=estimated,
            deviation_pct=deviation,
        ))

    flagged.sort(key=lambda item: abs(item.deviation_pct), reverse=True)
    return PriceCheckResponse(
        threshold_pct=threshold_pct,
        checked_count=len(segments),
        flagged_count=len(flagged),
        flagged=flagged,
    )


@router.get("", response_model=List[TransportSegmentResponse])
async def get_transport_segments(
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
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit the number of results"),
    offset: Optional[int] = Query(None, ge=0, description="Offset the results"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all transport segments with optional filtering.

    Examples:
    - `GET /transport-segments?transport_mode=bus`
    - `GET /transport-segments?from_node_name=almaty&to_node_name=shym`
    """
    # Stable order: without ORDER BY, limit/offset pages may overlap or skip rows.
    query = select(TransportSegment).order_by(TransportSegment.id)

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

    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{segment_id}", response_model=TransportSegmentResponse)
async def get_transport_segment(segment_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific transport segment by ID."""
    return await _get_segment_or_404(db, segment_id)


@router.post("",
             response_model=TransportSegmentResponse,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def create_segment(
    segment_data: TransportSegmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new transport segment.

    Only `from_node_id`, `to_node_id` and `transport_mode` are required.
    `distance_km`, `time_minutes`, `cost`, `co2_kg` and `comfort_score` are
    auto-estimated when omitted; anything you supply is stored as-is.

    Set `create_reverse: true` to also create the opposite direction with the
    same metrics (skipped silently if that edge already exists).

    Use `POST /transport-segments/estimate` to preview the values first.
    """
    _reject_self_loop(segment_data.from_node_id, segment_data.to_node_id)
    from_node = await _get_node_or_404(db, segment_data.from_node_id, "from_node_id")
    to_node   = await _get_node_or_404(db, segment_data.to_node_id,   "to_node_id")
    mode = segment_data.transport_mode

    # Check both directions up front so we fail BEFORE calling OSRM, with a
    # clear message instead of a raw database constraint error.
    pair = or_(
        (TransportSegment.from_node_id == from_node.id) & (TransportSegment.to_node_id == to_node.id),
        (TransportSegment.from_node_id == to_node.id) & (TransportSegment.to_node_id == from_node.id),
    )
    existing = (await db.execute(
        select(TransportSegment).filter(pair, TransportSegment.transport_mode == mode)
    )).scalars().all()
    forward_exists = any(s.from_node_id == from_node.id for s in existing)
    reverse_exists = any(s.from_node_id == to_node.id for s in existing)
    if forward_exists:
        raise HTTPException(
            status_code=409,
            detail=f"A {mode.value} segment from node {from_node.id} to node {to_node.id} "
                   f"already exists. Update it with PUT instead."
        )

    data = segment_data.model_dump(exclude={"create_reverse"})

    if data.get("distance_km") is None:
        # Distance unknown → look it up, then fill whatever else is missing.
        estimated = await _estimate_between(from_node, to_node, mode)
        defaults = {f: getattr(estimated, f) for f in _METRIC_FIELDS}
    else:
        # Distance supplied → derive the rest from it without a network call.
        defaults = _metrics_from_known_distance(mode, data["distance_km"])

    for field in _METRIC_FIELDS:
        if data.get(field) is None:
            data[field] = defaults[field]

    new_segment = TransportSegment(**data)
    db.add(new_segment)
    if segment_data.create_reverse and not reverse_exists:
        db.add(TransportSegment(**{
            **data, "from_node_id": to_node.id, "to_node_id": from_node.id,
        }))

    await db.commit()   # both directions in one transaction: all or nothing
    await db.refresh(new_segment)
    return new_segment


@router.post("/{segment_id}/recalculate",
             response_model=TransportSegmentResponse,
             dependencies=[Depends(require_api_key)])
async def recalculate_segment(
    segment_id: int,
    body: SegmentRecalculateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Overwrite the listed fields of an existing segment with fresh estimates.

    You must name the fields explicitly — nothing is overwritten by default,
    because stored values are often real, hand-checked numbers.

    - Including `distance_km` re-queries the distance from the node coordinates
      (use after moving a node).
    - Otherwise the stored distance is reused and no external call is made.
    """
    segment = await _get_segment_or_404(db, segment_id)
    mode = segment.transport_mode

    if "distance_km" in body.fields:
        from_node = await _get_node_or_404(db, segment.from_node_id, "from_node_id")
        to_node   = await _get_node_or_404(db, segment.to_node_id,   "to_node_id")
        estimated = await _estimate_between(from_node, to_node, mode)
        values = {f: getattr(estimated, f) for f in _METRIC_FIELDS}
    else:
        values = _metrics_from_known_distance(mode, segment.distance_km)

    for field in body.fields:
        setattr(segment, field, values[field])

    await db.commit()
    await db.refresh(segment)
    return segment


@router.put("/{segment_id}",
            response_model=TransportSegmentResponse,
            dependencies=[Depends(require_api_key)])
async def update_segment(
    segment_id: int,
    segment_data: TransportSegmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing transport segment (only provided fields change).

    If `transport_mode` or `distance_km` changes and `co2_kg` / `comfort_score`
    are not supplied, those two are **recalculated** from the new values.
    Time and cost are never changed implicitly — use `/recalculate` for that.
    """
    segment = await _get_segment_or_404(db, segment_id)

    update_data = segment_data.model_dump(exclude_unset=True)
    # An explicit null for a NOT NULL column would only fail later in the
    # database; treat "null" the same as "not provided".
    update_data = {k: v for k, v in update_data.items() if v is not None}

    new_from = update_data.get("from_node_id", segment.from_node_id)
    new_to   = update_data.get("to_node_id", segment.to_node_id)
    _reject_self_loop(new_from, new_to)
    if "from_node_id" in update_data:
        await _get_node_or_404(db, new_from, "from_node_id")
    if "to_node_id" in update_data:
        await _get_node_or_404(db, new_to, "to_node_id")

    effective_mode     = update_data.get("transport_mode", segment.transport_mode)
    effective_distance = update_data.get("distance_km", segment.distance_km)

    if "transport_mode" in update_data or "distance_km" in update_data:
        update_data.setdefault("co2_kg", estimate_co2(effective_mode, effective_distance))
        update_data.setdefault("comfort_score", default_comfort(effective_mode))

    for field, value in update_data.items():
        setattr(segment, field, value)

    await db.commit()
    await db.refresh(segment)
    return segment


@router.delete("/{segment_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_api_key)])
async def delete_segment(segment_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a transport segment."""
    segment = await _get_segment_or_404(db, segment_id)
    await db.delete(segment)
    await db.commit()
    return None
