"""
Database Models - SQLAlchemy 2.x with Mapped Types

ARCHITECTURE RULES:
1. Node + TransportSegment = Routing Graph (used by algorithm)
2. TouristPoint = Content (NOT part of routing)
3. PointNode = Bridge (last-mile access, applied AFTER routing)

All models use SQLAlchemy 2.x Mapped types for type safety.
"""

from typing import List, Optional
from sqlalchemy import String, Float, Integer, ForeignKey, Text, Enum as SQLEnum, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.enums import TransportMode, NodeType, AccessType


class Region(Base):
    """
    Geographic/administrative region for grouping tourist points.
    
    Example: "Almaty Region", "Turkestan Region"
    
    Relationships:
    - One region has many tourist points
    """
    __tablename__ = "regions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    tourist_points: Mapped[List["TouristPoint"]] = relationship(
        "TouristPoint",
        back_populates="region"
    )
    
    def __repr__(self) -> str:
        return f"<Region(id={self.id}, name='{self.name}')>"
    
    def __str__(self) -> str:
        return self.name


class TouristPointCategory(Base):
    """
    Hierarchical categories for tourist points.
    
    Self-referencing relationship allows tree structure:
    - Nature (parent)
      - Canyon (child)
      - Lake (child)
    - Culture (parent)
      - Mausoleum (child)
      - Museum (child)
    
    Relationships:
    - Self-referencing: parent/children for hierarchy
    - One category has many tourist points
    """
    __tablename__ = "tourist_point_categories"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tourist_point_categories.id"),
        nullable=True
    )
    
    # Self-referencing relationships for hierarchy
    parent: Mapped[Optional["TouristPointCategory"]] = relationship(
        "TouristPointCategory",
        remote_side="TouristPointCategory.id",
        back_populates="children"
    )
    children: Mapped[List["TouristPointCategory"]] = relationship(
        "TouristPointCategory",
        back_populates="parent"
    )
    
    # Tourist points in this category
    tourist_points: Mapped[List["TouristPoint"]] = relationship(
        "TouristPoint",
        back_populates="category"
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
    
    def __str__(self) -> str:
        return self.name


class Node(Base):
    """
    Transportation node - a vertex in the routing graph.
    
    Represents a physical location where transportation starts/ends.
    Examples: Almaty city, Shymkent Railway Station, Turkestan Bus Stop
    
    CRITICAL: Nodes are ONLY for transportation infrastructure.
    Tourist points are NOT nodes! They connect via PointNode.
    
    Relationships:
    - Source for many transport segments (outgoing)
    - Destination for many transport segments (incoming)
    - Connection point for many tourist points via PointNode
    """
    __tablename__ = "nodes"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    
    # Geographic coordinates
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Node type (city, airport, station, bus_stop)
    node_type: Mapped[NodeType] = mapped_column(
        SQLEnum(NodeType, native_enum=False),
        nullable=False
    )
    
    # Relationships
    # Segments where this node is the origin
    segments_from: Mapped[List["TransportSegment"]] = relationship(
        "TransportSegment",
        foreign_keys="TransportSegment.from_node_id",
        back_populates="from_node"
    )
    
    # Segments where this node is the destination
    segments_to: Mapped[List["TransportSegment"]] = relationship(
        "TransportSegment",
        foreign_keys="TransportSegment.to_node_id",
        back_populates="to_node"
    )
    
    # Last-mile connections to tourist points
    point_nodes: Mapped[List["PointNode"]] = relationship(
        "PointNode",
        back_populates="node"
    )
    
    def __repr__(self) -> str:
        return f"<Node(id={self.id}, name='{self.name}', type={self.node_type})>"
    
    def __str__(self) -> str:
        return self.name

# Slug Auto-Generation for Node Model
"""
@event.listens_for(Node, "before_insert")
def generate_node_slug(mapper, connection, target: Node):
    if not target.slug:
        target.slug = slugify(target.name)

@event.listens_for(Node, "before_update")
def node_before_update(mapper, connection, target: Node):
    if target.name:
        target.slug = slugify(target.name)
"""

class TransportSegment(Base):
    """
    Transport segment - an edge in the routing graph.
    
    Represents a direct connection between two nodes using specific transport.
    Example: Train from Almaty to Shymkent (14 hours, 3000 KZT)
    
    CRITICAL: This is the ONLY entity used by routing algorithms!
    The algorithm builds a graph from TransportSegments and finds paths.
    
    Multi-Criteria Fields:
    - time_minutes: Duration criterion
    - cost: Price criterion (in KZT - Kazakhstan Tenge)
    - comfort_score: Comfort criterion (1-10 scale)
    - co2_kg: Environmental criterion (CO2 emissions in kg)
    
    Relationships:
    - Links two nodes (from → to)
    """
    __tablename__ = "transport_segments"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Graph edge: from_node → to_node
    from_node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"),
        nullable=False,
        index=True
    )
    to_node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"),
        nullable=False,
        index=True
    )
    
    # Transport mode for this segment
    transport_mode: Mapped[TransportMode] = mapped_column(
        SQLEnum(TransportMode, native_enum=False),
        nullable=False
    )
    
    # Multi-criteria metrics for Pareto optimization
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False)  # In KZT (Tenge)
    comfort_score: Mapped[float] = mapped_column(Float, default=5.0)  # 1-10 scale
    co2_kg: Mapped[float] = mapped_column(Float, default=0.0)  # CO2 emissions in kg
    
    # Relationships
    from_node: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[from_node_id],
        back_populates="segments_from"
    )
    to_node: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[to_node_id],
        back_populates="segments_to"
    )
    
    def __repr__(self) -> str:
        return (
            f"<TransportSegment(id={self.id}, "
            f"from={self.from_node_id}→{self.to_node_id}, "
            f"mode={self.transport_mode})>"
        )
    
    def __str__(self) -> str:
        return f"{self.transport_mode}: {self.from_node_id} -> {self.to_node_id}"


class TouristPoint(Base):
    """
    Tourist destination - content entity.
    
    Represents a place to visit (NOT a transportation node!).
    Examples: Charyn Canyon, Mausoleum of Khoja Ahmed Yasawi
    
    CRITICAL ARCHITECTURE RULE:
    - TouristPoint is NEVER part of the routing graph
    - It does NOT act as a graph vertex
    - Routing algorithms do NOT know about tourist points
    - Connection to routing graph is via PointNode (last-mile access)
    
    Relationships:
    - Belongs to one region
    - Belongs to one category
    - Has many last-mile access options via PointNode
    """
    __tablename__ = "tourist_points"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Image URL for tourist point photo
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Geographic coordinates (for display, NOT for routing)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Optional metadata fields for enhanced UI display
    elevation_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Elevation in meters
    best_season: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "Apr - Oct"
    accessibility: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # e.g., "Open Daily", "Permit Required"

    
    # Foreign keys
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"),
        nullable=False,
        index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("tourist_point_categories.id"),
        nullable=False,
        index=True
    )
    
    # Relationships
    region: Mapped["Region"] = relationship("Region", back_populates="tourist_points")
    category: Mapped["TouristPointCategory"] = relationship(
        "TouristPointCategory",
        back_populates="tourist_points"
    )
    
    # Last-mile access options to reach this point
    point_nodes: Mapped[List["PointNode"]] = relationship(
        "PointNode",
        back_populates="tourist_point"
    )
    
    def __repr__(self) -> str:
        return f"<TouristPoint(id={self.id}, name='{self.name}')>"
    
    def __str__(self) -> str:
        return self.name

# Slug Auto-Generation for TouristPoint Model
"""@event.listens_for(TouristPoint, "before_insert")
def generate_tourist_point_slug(mapper, connection, target):
    if not target.slug:
        target.slug = slugify(target.name)

@event.listens_for(TouristPoint, "before_update")
def tourist_point_before_update(mapper, connection, target: TouristPoint):
    if target.name:
        target.slug = slugify(target.name)"""


class PointNode(Base):
    """
    Last-mile access - bridge between routing and tourism.
    
    Describes how to reach a TouristPoint from a nearby Node.
    Example: "From Turkestan city center → Taxi 2.3km → Mausoleum (7 min, 500 KZT)"
    
    CRITICAL ARCHITECTURE CONCEPT:
    - PointNode is NOT part of the routing graph!
    - Routing algorithm calculates: Start → ... → Node
    - Then PointNode is appended: Node → TouristPoint (last mile)
    - This keeps routing clean and separates concerns
    
    Multiple PointNodes per TouristPoint:
    - Same tourist point might be reachable from multiple nodes
    - Example: Charyn Canyon accessible from Almaty or nearby town
    - Routing tries each option and picks the best total route
    
    Relationships:
    - Connects one tourist point to one node
    - Describes access method (walk, taxi, shuttle, etc.)
    """
    __tablename__ = "point_nodes"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Foreign keys
    tourist_point_id: Mapped[int] = mapped_column(
        ForeignKey("tourist_points.id"),
        nullable=False,
        index=True
    )
    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"),
        nullable=False,
        index=True
    )
    
    # Access method (walk, taxi, shuttle, etc.)
    access_type: Mapped[AccessType] = mapped_column(
        SQLEnum(AccessType, native_enum=False),
        nullable=False
    )
    
    # Last-mile metrics
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0)  # In KZT
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    tourist_point: Mapped["TouristPoint"] = relationship(
        "TouristPoint",
        back_populates="point_nodes"
    )
    node: Mapped["Node"] = relationship("Node", back_populates="point_nodes")
    
    def __repr__(self) -> str:
        return (
            f"<PointNode(id={self.id}, "
            f"tourist_point={self.tourist_point_id}, "
            f"node={self.node_id}, "
            f"access={self.access_type})>"
        )
    
    def __str__(self) -> str:
        return f"{self.access_type}: Point {self.tourist_point_id} from Node {self.node_id}"
