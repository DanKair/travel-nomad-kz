import schemas, models
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from database import create_db_and_tables, get_db


@asynccontextmanager
#   Special function that FastAPI can use to run code before the application starts up
#   and after the application shuts down.  Handles startup and shutdown events.
async def lifespan(app: FastAPI):
    print("Lifespan start...")
    # This runs on startup, before the application begins accepting requests.
    create_db_and_tables()
    yield
    print("Lifespan end...")
app = FastAPI(lifespan=lifespan)

# Regions Endpoints
@app.get("/regions/", response_model=list[schemas.Region])
def list_regions(db: Session = Depends(get_db)):
    regions = db.query(models.Regions).all()
    return regions

@app.post("/regions/", response_model=schemas.Region)
def create_region(region: schemas.RegionCreate, db: Session = Depends(get_db)):
    # You can submit only region_name field actually here, slug would be generated automatically
    region_data = region.model_dump(include={'name', 'slug'})
    db_region = models.Regions(**region_data)
    db.add(db_region)
    db.commit()
    db.refresh(db_region)
    return db_region

@app.patch("/regions/{region_id}", response_model=schemas.Region)
def update_region(region_id: int, region_name: str, db: Session = Depends(get_db)):
    # 1. Find the region in the database by using "id" field
    target_region = db.query(models.Regions).filter(models.Regions.id == region_id).first()

    if target_region is None:
        raise HTTPException(status_code=404, detail="Region not found")

    target_region.name = region_name # Updating name of the region
    # Making our slug field also change
    from slugify import slugify
    target_region.slug = slugify(region_name)
    db.commit() # Saving the results
    db.refresh(target_region)
    return target_region


@app.get("/regions/{region_id}", response_model=schemas.Region)
def get_region(region_id: int, db: Session = Depends(get_db)):
    db_region = db.query(models.Regions).filter(models.Regions.id == region_id).first()
    if db_region is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return db_region

@app.get("/")
def read_root():
    return {"Hello": "World"}
