"""
Pydantic Schemas for Request/Response Validation

All schemas use Pydantic v2 with model_config for ORM mode.
Schemas are organized by domain entity.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.enums import TransportMode, NodeType, AccessType


# =============================================================================
# REGION SCHEMAS
# =============================================================================

class RegionBase(BaseModel):
    """Base schema with common region fields."""
    name: str = Field(..., max_length=100, description="Region name")
    description: Optional[str] = Field(None, description="Region description")


class RegionCreate(RegionBase):
    """Schema for creating a new region."""
    pass


class RegionUpdate(BaseModel):
    """Schema for updating a region (all fields optional)."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class RegionResponse(RegionBase):
    """Schema for region response."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# TOURIST POINT CATEGORY SCHEMAS
# =============================================================================

class CategoryBase(BaseModel):
    """Base schema with common category fields."""
    name: str = Field(..., max_length=100, description="Category name")
    parent_id: Optional[int] = Field(None, description="Parent category ID for hierarchy")


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""
    pass


class CategoryResponse(CategoryBase):
    """Schema for category response with ID."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# NODE SCHEMAS
# =============================================================================

class NodeBase(BaseModel):
    """Base schema with common node fields."""
    name: str = Field(..., max_length=200, description="Node name")
    slug: str = Field(..., max_length=200, description="URL-friendly identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    node_type: NodeType = Field(..., description="Type of transportation node")


class NodeCreate(NodeBase):
    """Schema for creating a new node."""
    pass


class NodeResponse(NodeBase):
    """Schema for node response."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# TRANSPORT SEGMENT SCHEMAS
# =============================================================================

class TransportSegmentBase(BaseModel):
    """Base schema with common transport segment fields."""
    from_node_id: int = Field(..., description="Origin node ID")
    to_node_id: int = Field(..., description="Destination node ID")
    transport_mode: TransportMode = Field(..., description="Transportation mode")
    distance_km: float = Field(..., gt=0, description="Distance in kilometers")
    time_minutes: int = Field(..., gt=0, description="Travel time in minutes")
    cost: float = Field(..., ge=0, description="Cost in KZT (Kazakhstan Tenge)")
    comfort_score: float = Field(5.0, ge=1, le=10, description="Comfort rating (1-10)")
    co2_kg: float = Field(0.0, ge=0, description="CO2 emissions in kg")

class TransportSegmentCreate(TransportSegmentBase):
    """Schema for creating a new transport segment."""
    pass


class TransportSegmentUpdate(BaseModel):
    from_node_id: Optional[int] = None
    to_node_id: Optional[int] = None
    transport_mode: Optional[TransportMode] = None

    distance_km: Optional[float] = Field(None, gt=0)
    time_minutes: Optional[int] = Field(None, gt=0)
    cost: Optional[float] = Field(None, ge=0)

    comfort_score: Optional[float] = Field(None, ge=1, le=10)
    co2_kg: Optional[float] = Field(None, ge=0)


class TransportSegmentResponse(TransportSegmentBase):
    """Schema for transport segment response."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# TOURIST POINT SCHEMAS
# =============================================================================

class TouristPointBase(BaseModel):
    """Base schema with common tourist point fields."""
    name: str = Field(..., max_length=200, description="Tourist point name")
    # TODO: Make it Optional Field for slug Auto-generation
    slug: str = Field(..., max_length=200, description="URL-friendly identifier")
    description: Optional[str] = Field(None, description="Detailed description")
    image_url: Optional[str] = Field(None, max_length=500, description="Image URL")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    region_id: int = Field(..., description="Region ID")
    category_id: int = Field(..., description="Category ID")
    
    # Optional metadata fields
    elevation_m: Optional[int] = Field(None, description="Elevation in meters")
    best_season: Optional[str] = Field(None, max_length=100, description="Best visiting season")
    accessibility: Optional[str] = Field(None, max_length=200, description="Accessibility information")



class TouristPointCreate(TouristPointBase):
    """Schema for creating a new tourist point."""
    pass


class TouristPointUpdate(BaseModel):
    """Schema for updating a tourist point (all fields optional)."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    region_id: Optional[int] = None
    category_id: Optional[int] = None
    
    # Optional metadata fields
    elevation_m: Optional[int] = None
    best_season: Optional[str] = Field(None, max_length=100)
    accessibility: Optional[str] = Field(None, max_length=200)



class TouristPointResponse(TouristPointBase):
    """Schema for tourist point response with nested region and category."""
    id: int
    region: RegionResponse
    category: CategoryResponse
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# POINT NODE SCHEMAS (Last-Mile Access)
# =============================================================================

class PointNodeBase(BaseModel):
    """Base schema with common point node fields."""
    tourist_point_id: int = Field(..., description="Tourist point ID")
    node_id: int = Field(..., description="Node ID")
    access_type: AccessType = Field(..., description="Last-mile access type")
    distance_km: float = Field(..., gt=0, description="Last-mile distance in km")
    time_minutes: int = Field(..., gt=0, description="Last-mile time in minutes")
    cost: float = Field(0.0, ge=0, description="Last-mile cost in KZT")
    description: Optional[str] = Field(None, description="Access instructions")


class PointNodeCreate(PointNodeBase):
    """Schema for creating a new point node."""
    pass


class PointNodeResponse(PointNodeBase):
    """Schema for point node response."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# ROUTING SCHEMAS
# =============================================================================

class RouteRequest(BaseModel):
    """
    Schema for route calculation request.
    
    Query parameters:
    - from_node: Slug of starting node (e.g., "almaty")
    - to_tourist_point: Slug of destination tourist point (e.g., "mausoleum-yasawi")
    - Optional weight customization for multi-criteria optimization
    """
    from_node: str = Field(..., description="Starting node slug")
    to_tourist_point: str = Field(..., description="Destination tourist point slug")
    
    # Optional: Custom weights for multi-criteria optimization (must sum to 1.0)
    time_weight: Optional[float] = Field(None, ge=0, le=1, description="Time importance (0-1)")
    cost_weight: Optional[float] = Field(None, ge=0, le=1, description="Cost importance (0-1)")
    comfort_weight: Optional[float] = Field(None, ge=0, le=1, description="Comfort importance (0-1)")
    co2_weight: Optional[float] = Field(None, ge=0, le=1, description="CO2 importance (0-1)")


class RouteSegmentStep(BaseModel):
    """
    Single step in the route (one transport segment).
    
    Represents traveling from one node to another using a specific transport mode.
    """
    from_node_name: str
    from_node_lat: Optional[float] = None
    from_node_lon: Optional[float] = None
    to_node_name: str
    to_node_lat: Optional[float] = None
    to_node_lon: Optional[float] = None
    transport_mode: TransportMode
    distance_km: float
    time_minutes: int
    cost: float
    comfort_score: float
    co2_kg: float


class LastMileAccess(BaseModel):
    """
    Last-mile access information to reach the tourist point.
    
    This is appended AFTER the main route calculation.
    """
    from_node_name: str
    from_node_lat: Optional[float] = None
    from_node_lon: Optional[float] = None
    to_point_lat: Optional[float] = None
    to_point_lon: Optional[float] = None
    access_type: AccessType
    distance_km: float
    time_minutes: int
    cost: float
    description: Optional[str]


class RouteResponse(BaseModel):
    """
    Complete route response with all details.
    
    Contains:
    - List of route steps (transport segments)
    - Last-mile access instructions
    - Total aggregated metrics
    - Optimization score
    """
    from_node: str
    to_tourist_point: str
    
    # Route steps (main transportation)
    route_steps: List[RouteSegmentStep]
    
    # Last-mile access
    last_mile_access: LastMileAccess
    
    # Totals (including last mile)
    total_distance_km: float
    total_time_minutes: int
    total_cost: float
    total_co2_kg: float
    average_comfort: float
    
    # Optimization score (lower is better)
    optimization_score: float
    
    model_config = ConfigDict(from_attributes=True)
