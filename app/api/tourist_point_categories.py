from idlelib.query import Query
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TouristPointCategory
from app.schemas import CategoryResponse, CategoryCreate

router = APIRouter(prefix="/tourist-point-categories", tags=["Tourist Point Categories"])

@router.get("", response_model=List[CategoryResponse])
def get_tourist_point_categories(db: Session = Depends(get_db)):
    categories = db.query(TouristPointCategory).all()
    return categories

@router.get("/{category_id}", response_model=CategoryResponse)
def get_tourist_point_category(category_id: int, db: Session = Depends(get_db)):
    tourist_point_category = db.query(TouristPointCategory).get(category_id)
    if not tourist_point_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return tourist_point_category

# TODO: Make parent_id Optional Field (that's why I made parent_id == 0 logic)
@router.post("/{category_id}", response_model=CategoryCreate)
def create_category(category_name: str, parent_id: Optional[int], db: Session = Depends(get_db)):
    if parent_id == 0:
        new_category = TouristPointCategory(name=category_name, parent_id=None)
        db.add(new_category)
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        return new_category

    new_category = TouristPointCategory(name=category_name, parent_id=parent_id)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.delete("/{category_id}", response_model=str)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    target_category = db.query(TouristPointCategory).get(category_id)
    if not target_category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(target_category)
    db.commit()
    return f"Category: '{target_category.name}' was deleted"
