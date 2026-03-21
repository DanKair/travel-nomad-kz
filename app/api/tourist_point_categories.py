from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models import TouristPointCategory
from app.schemas import CategoryResponse, CategoryCreate
from app.core.auth import require_api_key

router = APIRouter(prefix="/tourist-point-categories", tags=["Tourist Point Categories"])

@router.get("", response_model=List[CategoryResponse])
async def get_tourist_point_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TouristPointCategory))
    categories = result.scalars().all()
    return categories

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_tourist_point_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TouristPointCategory).filter(TouristPointCategory.id == category_id))
    tourist_point_category = result.scalars().first()
    if not tourist_point_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return tourist_point_category

# TODO: Make parent_id Optional Field
@router.post("", 
             response_model=CategoryResponse, 
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_api_key)])
async def create_category(category_data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a new category."""
    new_category = TouristPointCategory(**category_data.model_dump())
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category

@router.delete("/{category_id}", 
               response_model=str,
               dependencies=[Depends(require_api_key)])
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TouristPointCategory).filter(TouristPointCategory.id == category_id))
    target_category = result.scalars().first()
    if not target_category:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(target_category)
    await db.commit()
    return f"Category: '{target_category.name}' was deleted"
