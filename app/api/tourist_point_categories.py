from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import TouristPointCategory
from app.schemas import CategoryResponse, CategoryCreate

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

# TODO: Make parent_id Optional Field (that's why I made parent_id == 0 logic)
@router.post("/{category_id}", response_model=CategoryCreate)
async def create_category(category_name: str, parent_id: Optional[int], db: AsyncSession = Depends(get_db)):
    if parent_id == 0:
        new_category = TouristPointCategory(name=category_name, parent_id=None)
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        return new_category

    new_category = TouristPointCategory(name=category_name, parent_id=parent_id)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category

@router.delete("/{category_id}", response_model=str)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TouristPointCategory).filter(TouristPointCategory.id == category_id))
    target_category = result.scalars().first()
    if not target_category:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(target_category)
    await db.commit()
    return f"Category: '{target_category.name}' was deleted"
