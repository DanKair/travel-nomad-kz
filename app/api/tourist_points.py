"""
Tourist Points API Endpoints

Provides CRUD operations and filtering for tourist points.
"""
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from geopy import Nominatim
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.coordinates import geocode_async

from app.config import settings
from app.database import get_db
from app.models import TouristPoint, Region, TouristPointCategory
from app.schemas import TouristPointCreate, TouristPointUpdate, TouristPointResponse


router = APIRouter(prefix="/tourist-points", tags=["Tourist Points"])


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
        .options(joinedload(TouristPoint.region), joinedload(TouristPoint.category))
    )
    
    # Apply filters if provided
    if region_id is not None:
        query = query.filter(TouristPoint.region_id == region_id)
    
    if category_id is not None:
        query = query.filter(TouristPoint.category_id == category_id)
    
    result = await db.execute(query)
    tourist_points = result.scalars().all()
    return tourist_points


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
        .options(joinedload(TouristPoint.region), joinedload(TouristPoint.category))
        .filter(TouristPoint.id == point_id)
    )
    point = result.scalars().first()
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tourist point with id {point_id} not found"
        )
    return point


@router.post("", response_model=TouristPointResponse, status_code=status.HTTP_201_CREATED)
async def create_tourist_point(point_data: TouristPointCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new tourist point.
    
    Args:
        point_data: Tourist point creation data
    
    Returns:
        Created tourist point
    
    Raises:
        400: If tourist point with same slug already exists
    """
    # Creating slug if missing
    if not point_data.slug:
        point_data.slug = slugify(point_data.name)


    # Check if tourist point with same slug exists
    result = await db.execute(select(TouristPoint).filter(TouristPoint.slug == point_data.slug))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tourist point with slug '{point_data.slug}' already exists"
        )

    # 3) Auto-geocode if coords are not provided
    if point_data.latitude is None or point_data.longitude is None:
        try:
            location = await geocode_async(point_data.name)
            if not location:
                raise HTTPException(
                    status_code=404,
                    detail="Cannot find coordinates for this place"
                )
            point_data.latitude = float(location["lat"])
            point_data.longitude = float(location["lon"])

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Geocoding error: {e}")
    
    # Create new tourist point
    point = TouristPoint(**point_data.model_dump())
    db.add(point)
    await db.commit()
    await db.refresh(point)
    return point

@router.patch("/{point_id}", response_model=TouristPointResponse)
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
    result = await db.execute(
        select(TouristPoint)
        .options(joinedload(TouristPoint.region), joinedload(TouristPoint.category))
        .where(TouristPoint.id == point_id)
    )
    point = result.scalar_one_or_none()
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tourist point with id {point_id} not found"
        )
    # Check if Region Mapping Correct
    if point_data.region_id is not None:
        result = await db.execute(select(Region).where(Region.id == point_data.region_id))
        region_exists = result.scalar_one_or_none()

        if not region_exists:
            raise HTTPException(
                status_code=400,
                detail="Invalid region_id"
            )

    # Check for Category FK
    if point_data.category_id is not None:
        result = await db.execute(select(TouristPointCategory).where(TouristPointCategory.id == point_data.category_id))
        category_exists = result.scalar_one_or_none()

        if not category_exists:
            raise HTTPException(
                status_code=400,
                detail="Invalid category_id"
            )

    # Update fields
    update_data = point_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(point, field, value)

    await db.commit()
    await db.refresh(point)
    return point

@router.delete("/{point_id}", response_model=str)
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
    await db.delete(target_point)
    await db.commit()
    return f"Tourist point: {target_point.name} was deleted"


# Filtering
@router.get("/region/{region_id}", response_model=List[TouristPointResponse])
async def get_tourist_points_by_region(region_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TouristPoint)
        .options(joinedload(TouristPoint.region), joinedload(TouristPoint.category))
        .filter(TouristPoint.region_id == region_id)
    )
    return result.scalars().all()
