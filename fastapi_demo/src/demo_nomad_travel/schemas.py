from pydantic import BaseModel, Field, model_validator
from slugify import slugify

# Tourist Points

class TouristPointBase(BaseModel):
    name: str = Field(max_length=100)
    short_description: str =  None
    long_description: str | None


class TouristPoint(TouristPointBase):
    id: int
    region_id: int

    class Config:
        orm_mode = True

# Regions
class RegionBase(BaseModel):
    name: str = Field(max_length=50)


class RegionCreate(RegionBase):
    slug: str | None = None
    # description: str | None = None # Commented to make create_region endpoint work simply
    tourist_points: list[TouristPoint] = []

    class Config:
        orm_mode = True

    @model_validator(mode="before")
    @classmethod
    def generate_slug_from_name(cls, data: dict) -> dict:
        """Generates a slug from the name field before Pydantic validation."""
        if isinstance(data, dict) and "name" in data and not data.get("slug"):
            data["slug"] = slugify(data["name"])
        return data


class Region(RegionBase):
    '''
    This class represents a region used for API Responses, cause it contain "field" lol.
    Actually I need to improve this, but later on...
    '''
    id: int
    slug: str
    tourist_points: list[TouristPoint] = []

    class Config:
        orm_mode = True

