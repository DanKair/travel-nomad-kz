"""
Region API Endpoints

Provides CRUD operations for regions (geographic/administrative groupings).
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import Region
from app.schemas import RegionCreate, RegionUpdate, RegionResponse


router = APIRouter(prefix="/regions", tags=["Regions"])


@router.get("", response_model=List[RegionResponse])
async def get_regions(db: AsyncSession = Depends(get_db)):
    """
    Get all regions.
    
    Returns:
        List of all regions in the database
    """
    result = await db.execute(select(Region))
    regions = result.scalars().all()
    return regions


@router.get("/{region_id}", response_model=RegionResponse)
async def get_region(region_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific region by ID.
    
    Args:
        region_id: Region ID
    
    Returns:
        Region details
    
    Raises:
        404: If region not found
    """
    result = await db.execute(select(Region).filter(Region.id == region_id))
    region = result.scalars().first()
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with id {region_id} not found"
        )
    return region


@router.post("", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
async def create_region(region_data: RegionCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new region.
    
    Args:
        region_data: Region creation data
    
    Returns:
        Created region
    
    Raises:
        400: If region with same name already exists
    """
    # Check if region with same name exists
    result = await db.execute(select(Region).filter(Region.name == region_data.name))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Region with name '{region_data.name}' already exists"
        )
    
    # Create new region
    region = Region(**region_data.model_dump())
    db.add(region)
    await db.commit()
    await db.refresh(region)
    return region


@router.patch("/{region_id}", response_model=RegionResponse)
async def update_region(
    region_id: int,
    region_data: RegionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing region.
    
    Args:
        region_id: Region ID
        region_data: Fields to update
    
    Returns:
        Updated region
    
    Raises:
        404: If region not found
    """
    result = await db.execute(select(Region).filter(Region.id == region_id))
    region = result.scalars().first()
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with id {region_id} not found"
        )
    
    # Update fields
    update_data = region_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(region, field, value)
    
    await db.commit()
    await db.refresh(region)
    return region

@router.delete("/regions/{region_id}", response_model=str)
async def delete_region(region_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).filter(Region.id == region_id))
    target_region = result.scalars().first()
    if target_region is None:
        raise HTTPException(status_code=404, detail="Region not found")

    deleted_region = target_region.name
    await db.delete(target_region)
    await db.commit()
    return f"{deleted_region} has been removed."