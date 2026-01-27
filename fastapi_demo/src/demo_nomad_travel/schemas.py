from pydantic import BaseModel, Field

# Regions
class RegionCreate(BaseModel):
    name: str = Field(max_length=50)
    class Config:
        orm_mode = True


class RegionUpdate(BaseModel):
    '''
    This class represents a region used for API Responses, UPDATE operations particularly,
    cause it contains "id" field lol.
    Actually I need to improve this, but later on...
    '''
    id: int
    name: str | None = None

    class Config:
        orm_mode = True

class RegionRead(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True

# TouristPoint
class TouristPointBase(BaseModel):
    name: str = Field(max_length=100)
    short_description: str | None = None
    long_description: str | None = None
    # There should be category selection ENUM
    category_id: int

class TouristPointCreate(TouristPointBase):
    region_id: int


class TouristPointRead(TouristPointBase):
    id: int
    region_id: int

    class Config:
        from_attributes = True


class TouristPointUpdate(BaseModel):
    name: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    category_id: int | None = None
