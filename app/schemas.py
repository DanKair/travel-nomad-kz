"""
Pydantic Schemas for Request/Response Validation

All schemas use Pydantic v2 with model_config for ORM mode.
Schemas are organized by domain entity.
"""
from decimal import Decimal
from typing import Optional, List, Literal
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
    slug: Optional[str] = Field(None    , max_length=200, description="URL-friendly identifier")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    node_type: NodeType = Field(..., description="Type of transportation node")


class NodeCreate(NodeBase):
    """Schema for creating a new node."""
    pass


class NodeUpdate(BaseModel):
    """Schema for updating a node (all fields optional)."""
    name: Optional[str] = Field(None, max_length=200, description="Node name")
    slug: Optional[str] = Field(None, max_length=200, description="URL-friendly identifier")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    node_type: Optional[NodeType] = Field(None, description="Type of transportation node")


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
    time_minutes: Optional[int] = Field(
        None, gt=0,
        description="Travel time in minutes. Leave blank to auto-estimate "
                    "(OSRM duration for road modes, speed model otherwise). "
                    "Supply it when you know the real schedule."
    )
    cost: Optional[Decimal] = Field(
        None, ge=0,
        description="Cost in KZT. Leave blank to auto-estimate from the tariff model."
    )
    distance_km: Optional[float] = Field(
        None, gt=0,
        description="Distance in km. Leave blank to auto-calculate from node coordinates."
    )
    comfort_score: Optional[float] = Field(
        None, ge=1, le=10,
        description="Comfort rating 1–10. Leave blank to auto-calculate from transport_mode."
    )
    co2_kg: Optional[float] = Field(
        None, ge=0,
        description="CO2 in kg. Leave blank to auto-calculate: CO2_PER_KM[mode] × distance_km."
    )

class TransportSegmentCreate(TransportSegmentBase):
    """Schema for creating a new transport segment."""
    create_reverse: bool = Field(
        False,
        description="Also create the opposite direction (to → from) with the same "
                    "metrics. The routing graph is directed, so a two-way "
                    "connection needs both edges."
    )


class SegmentEstimateRequest(BaseModel):
    """Request schema for the dry-run /estimate endpoint."""
    from_node_id: int = Field(..., description="Origin node ID")
    to_node_id: int = Field(..., description="Destination node ID")
    transport_mode: TransportMode = Field(..., description="Transportation mode to estimate for")


class SegmentEstimateResponse(BaseModel):
    """Response from /estimate — preview every auto-calculated value before committing."""
    transport_mode: TransportMode
    distance_km: float
    time_minutes: int
    cost: Decimal
    co2_kg: float
    comfort_score: float
    distance_strategy: str = Field(
        ..., description="haversine | osrm | haversine_x_detour | haversine_fallback (OSRM was unreachable)"
    )
    time_strategy: str = Field(..., description="osrm_duration | speed_model")


SegmentField = Literal["distance_km", "time_minutes", "cost", "co2_kg", "comfort_score"]


class SegmentRecalculateRequest(BaseModel):
    """Which stored fields to overwrite with fresh estimates."""
    fields: List[SegmentField] = Field(
        ..., min_length=1,
        description="Fields to re-estimate. Only these are overwritten; everything else is kept."
    )


class PriceCheckItem(BaseModel):
    """One segment whose stored price disagrees with the tariff model."""
    segment_id: int
    from_node: str
    to_node: str
    transport_mode: TransportMode
    distance_km: float
    stored_cost: Decimal
    estimated_cost: Decimal
    deviation_pct: float = Field(..., description="+ = stored price above the model, - = below")


class PriceCheckResponse(BaseModel):
    threshold_pct: float
    checked_count: int
    flagged_count: int
    flagged: List[PriceCheckItem]


class TransportSegmentUpdate(BaseModel):
    from_node_id: Optional[int] = None
    to_node_id: Optional[int] = None
    transport_mode: Optional[TransportMode] = None

    distance_km: Optional[float] = Field(None, gt=0)
    time_minutes: Optional[int] = Field(None, gt=0)
    cost: Optional[Decimal] = Field(None, ge=0)

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
    slug: Optional[str] = Field(None, max_length=200, description="URL-friendly identifier")
    description: Optional[str] = Field(None, description="Detailed description")
    image_url: Optional[str] = Field(None, max_length=500, description="Image URL")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
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
    slug: Optional[str] = Field(None, max_length=200)
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
    has_route: bool = False  # True if at least one PointNode (last-mile access) exists
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# POINT NODE SCHEMAS (Last-Mile Access)
# =============================================================================

class PointNodeBase(BaseModel):
    """Base schema with common point node fields."""
    tourist_point_id: int = Field(..., description="Tourist point ID")
    node_id: int = Field(..., description="Node ID")
    access_type: AccessType = Field(..., description="Last-mile access type")
    distance_km: Optional[float] = Field(None, gt=0, description="Last-mile distance in km")
    time_minutes: Optional[int] = Field(None, gt=0, description="Last-mile time in minutes")
    cost: Optional[Decimal] = Field(None, ge=0, description="Last-mile cost in KZT. Leave blank to auto-estimate.")
    comfort_score: Optional[float] = Field(None, ge=1, le=10, description="Last-mile comfort score")
    co2_kg: Optional[float] = Field(None, ge=0, description="Last-mile CO2 in kg")
    description: Optional[str] = Field(None, description="Access instructions")


class PointNodeCreate(PointNodeBase):
    """Schema for creating a new point node."""
    pass


class PointNodeEstimateRequest(BaseModel):
    """Request schema for dry-run point node estimation."""
    tourist_point_id: int = Field(..., description="Tourist point ID")
    node_id: int = Field(..., description="Node ID")
    access_type: AccessType = Field(..., description="Last-mile access type")


class PointNodeEstimateResponse(BaseModel):
    """Response schema for point node estimation."""
    access_type: AccessType
    distance_km: float
    time_minutes: int
    cost: Decimal
    co2_kg: float
    comfort_score: float
    distance_strategy: str
    time_strategy: str


class PointNodeAutoConnectRequest(BaseModel):
    """Link a tourist point to its nearest transport node(s) in one call."""
    tourist_point_id: int = Field(..., description="Tourist point ID")
    max_nodes: int = Field(1, ge=1, le=5, description="How many nearest nodes to connect")
    max_radius_km: float = Field(
        300, gt=0, le=1000,
        description="Ignore nodes further away than this (straight-line distance)"
    )
    access_type: Optional[AccessType] = Field(
        None,
        description="Access type to use. Default: walk when the node is within "
                    "1.5 km, taxi otherwise."
    )


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
    cost: Decimal
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
    cost: Decimal
    comfort_score: float
    co2_kg: float
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
    total_cost: Decimal
    total_co2_kg: float
    average_comfort: float
    
    # Optimization score (lower is better)
    optimization_score: float
    
    model_config = ConfigDict(from_attributes=True)


class RouteAlternative(RouteResponse):
    """
    A single profile alternative — extends RouteResponse with labeling metadata.

    Each alternative represents the optimal path for ONE specific optimization
    profile (fastest / cheapest / comfort / eco / optimal).

    When two profiles produce identical paths (same sequence of segments),
    they are merged into a single RouteAlternative with combined tags instead
    of returning duplicates.
    """
    profile: str = Field(..., description="Profile key: fastest | cheapest | comfort | eco | optimal")
    label: str = Field(..., description="Human-readable profile name, e.g. 'Fastest'")
    is_recommended: bool = Field(False, description="True for the balanced 'optimal' profile")
    tags: List[str] = Field(default_factory=list, description="Extra labels when profile merges, e.g. ['Also Cheapest']")


class RouteAlternativesResponse(BaseModel):
    """
    Top-level response for GET /routes/alternatives.

    Contains all deduplicated profile alternatives ordered with 'optimal' first.
    Identical paths across profiles are merged — the surviving entry receives
    extra tags (e.g. 'Also Cheapest') instead of being duplicated.
    """
    from_node: str
    to_tourist_point: str
    alternatives: List[RouteAlternative]


# =============================================================================
# DATA MANAGEMENT SCHEMAS
# =============================================================================

class DataUpdateResult(BaseModel):
    """Schema for individual segment update result."""
    segment_id: int
    success: bool
    old_cost: Decimal
    new_cost: Decimal
    old_time_minutes: int
    new_time_minutes: int
    source: str
    error: Optional[str] = None


class DataUpdateBatchResponse(BaseModel):
    """Response schema for batch segment updates."""
    updated_count: int
    failed_count: int
    results: List[DataUpdateResult]