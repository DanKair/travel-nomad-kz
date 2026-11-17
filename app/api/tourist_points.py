"""
Tourist Points API Endpoints

Provides CRUD operations and filtering for tourist points.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.coordinates import geocode_async, GeocodingUnavailable

from app.core.database import get_db
from app.models import TouristPoint, Region, TouristPointCategory
from app.schemas import TouristPointCreate, TouristPointUpdate, TouristPointResponse
from app.core.auth import require_api_key


router = APIRouter(prefix="/tourist-points", tags=["Tourist Points"])


_FULL_LOAD = (
    joinedload(TouristPoint.region),
    joinedload(TouristPoint.category),
    selectinload(TouristPoint.point_nodes),  # needed for has_route
)


async def _load_point(db: AsyncSession, point_id: int) -> Optional[TouristPoint]:
    """Fetch one point with everything the response schema touches, fresh from the DB."""
    result = await db.execute(
        select(TouristPoint)
        .options(*_FULL_LOAD)
        .filter(TouristPoint.id == point_id)
        .execution_options(populate_existing=True)
    )
    return result.scalars().first()


async def _require_region_and_category(db: AsyncSession, region_id, category_id) -> None:
    if region_id is not None:
        if not (await db.execute(select(Region.id).where(Region.id == region_id))).first():
            raise HTTPException(status_code=400, detail="Invalid region_id")
    if category_id is not None:
        if not (await db.execute(
            select(TouristPointCategory.id).where(TouristPointCategory.id == category_id)
        )).first():
            raise HTTPException(status_code=400, detail="Invalid category_id")


def _with_has_route(point: TouristPoint) -> TouristPointResponse:
    """Convert ORM model to response schema, computing has_route from loaded point_nodes."""
    data = TouristPointResponse.model_validate(point)
    data.has_route = len(point.point_nodes) > 0
    return data


@router.get("", response_model=List[TouristPointResponse])
async def get_tourist_points(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tourist points with optional filtering.
    
    Args:
        region_id: Optional filter by region
        category_id: Optional filter by category
    
    Returns:
        List of tourist points matching filters
    """
    query = (
        select(TouristPoint)
        .options(
            joinedload(TouristPoint.region),
            joinedload(TouristPoint.category),
            selectinload(TouristPoint.point_nodes),  # needed for has_route
        )
    )
    
    # Apply filters if provided
    if region_id is not None:
        query = query.filter(TouristPoint.region_id == region_id)
    
    if category_id is not None:
        query = query.filter(TouristPoint.category_id == category_id)
    
    result = await db.execute(query)
    tourist_points = result.scalars().all()
    return [_with_has_route(p) for p in tourist_points]


@router.get("/{point_id}", response_model=TouristPointResponse)
async def get_tourist_point(point_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific tourist point by ID.
    
    Args:
        point_id: Tourist point ID
    
    Returns:
        Tourist point details with nested region and category
    
    Raises:
        404: If tourist point not found
    """
    result = await db.execute(
        select(TouristPoint)
        .options(
            joinedload(TouristPoint.region),
            joinedload(TouristPoint.category),
            selectinload(TouristPoint.point_nodes),
        )
        .filter(TouristPoint.id == point_id)
    )
    point = result.scalars().first()
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tourist point with id {point_id} not found"
        )
    return _with_has_route(point)


@router.post("", 
             response_model=TouristPointResponse, 
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def create_tourist_point(
    tp_data: TouristPointCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a tourist point. `slug` is generated from the name and coordinates
    are geocoded from the name when omitted.

    The new point is not routable yet — follow up with
    `POST /point-nodes/auto-connect` to link it to the nearest transport node.
    """
    if not tp_data.slug:
        tp_data.slug = slugify(tp_data.name)

    result = await db.execute(select(TouristPoint).filter(TouristPoint.slug == tp_data.slug))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail=f"Tourist point with slug '{tp_data.slug}' already exists")

    # Validate foreign keys BEFORE the (slow, external) geocoding call.
    await _require_region_and_category(db, tp_data.region_id, tp_data.category_id)

    if tp_data.latitude is None or tp_data.longitude is None:
        try:
            location = await geocode_async(tp_data.name)
        except GeocodingUnavailable:
            raise HTTPException(
                status_code=503,
                detail="Geocoding service is unavailable. Retry later or supply "
                       "latitude and longitude explicitly."
            )
        if not location:
            raise HTTPException(
                status_code=422,
                detail=f"Could not find coordinates for '{tp_data.name}'. "
                       f"Supply latitude and longitude explicitly."
            )
        tp_data.latitude = float(location["lat"])
        tp_data.longitude = float(location["lon"])

    point = TouristPoint(**tp_data.model_dump())
    db.add(point)
    await db.flush()          # sends the INSERT so the database assigns the id
    point_id = point.id       # read it now: commit() expires every attribute
    await db.commit()

    return _with_has_route(await _load_point(db, point_id))

@router.put("/{point_id}", 
            response_model=TouristPointResponse,
            dependencies=[Depends(require_api_key)])
async def update_tourist_point(
    point_id: int,
    point_data: TouristPointUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing tourist point.

    Args:
        point_id: Tourist point ID
        point_data: Fields to update

    Returns:
        Updated tourist point

    Raises:
        404: If tourist point not found
    """
    point = await _load_point(db, point_id)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tourist point with id {point_id} not found"
        )
    await _require_region_and_category(db, point_data.region_id, point_data.category_id)

    update_data = point_data.model_dump(exclude_unset=True)

    # Renaming regenerates the slug unless one was supplied explicitly.
    if update_data.get("name") and not update_data.get("slug"):
        update_data["slug"] = slugify(update_data["name"])

    for field, value in update_data.items():
        if value is None and field in ("name", "slug", "region_id", "category_id"):
            continue  # NOT NULL columns: null means "leave as is"
        setattr(point, field, value)

    await db.commit()
    # Re-query instead of refresh(): refresh reloads columns but leaves the
    # already-loaded `region` / `category` objects pointing at the OLD rows.
    return _with_has_route(await _load_point(db, point_id))

@router.delete("/{point_id}", 
               response_model=str,
               dependencies=[Depends(require_api_key)])
async def delete_tourist_point(
    point_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TouristPoint).filter(TouristPoint.id == point_id))
    target_point = result.scalars().first()
    if not target_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tourist point with id {point_id} not found"
        )
    # Read the name BEFORE commit: afterwards the object is expired and deleted,
    # so touching an attribute would try to reload a row that no longer exists.
    name = target_point.name
    await db.delete(target_point)   # cascades to its point_nodes
    await db.commit()
    return f"Tourist point: {name} was deleted"


# Filtering
@router.get("/region/{region_id}", response_model=List[TouristPointResponse])
async def get_tourist_points_by_region(region_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TouristPoint).options(*_FULL_LOAD).filter(TouristPoint.region_id == region_id)
    )
    return [_with_has_route(p) for p in result.scalars().all()]
