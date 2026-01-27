from typing import List, Optional

from slugify import slugify
from sqlalchemy import (
    Integer,
    String,
    ForeignKey,
    Text, Float, Enum as SQLEnum, DECIMAL, event  # to don't confuse it with Python's built-in Enum class
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from enums import NodeType, TransportMode, AccessType


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = 'regions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False) # Mapped makes convert our datatype to our DB's type (like VarChar 50)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # ✅ Relationship to tourist_points
    tourist_points: Mapped[List['TouristPoint']] = relationship(
        back_populates='region', # references to region field in TouristPoint class
        cascade='all, delete-orphan',
    )

# Slug Auto-Generation for Region Model
@event.listens_for(Region, "before_insert")
def generate_region_slug(mapper, connection, target):
    if not target.slug:
        target.slug = slugify(target.name)

@event.listens_for(Region, "before_update")
def region_before_update(mapper, connection, target: Region):
    if target.name:
        target.slug = slugify(target.name)


class TouristPoint(Base):
    """
    Content entity representing a tourist destination.

    Stores everything that makes a location interesting to tourists:
    - Cultural and historical significance
    - Visitor information and recommendations
    - Multimedia content (photos, descriptions)
    - Administrative metadata

    Philosophy: TouristPoints are content abstractions. They exist to inform
    and inspire visitors. A tourist point cares deeply about stories, experiences,
    and what makes a place special—not about graph algorithms or spatial indexing.

    The one-to-one relationship with Node says: "This tourist destination exists
    at a specific location." The location is important, but it's not the essence
    of what makes this a tourist point.
    """
    __tablename__ = 'tourist_points'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_description: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    long_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Foreign Keys
    region_id: Mapped[int] = mapped_column(ForeignKey('regions.id'))
    category_id: Mapped[int] = mapped_column(ForeignKey("tourist_point_categories.id"))


    # Relationships
    region: Mapped['Region'] = relationship(back_populates='tourist_points')
    category: Mapped['TouristPointCategory'] = relationship(back_populates='tourist_points')
    # PointNode Related (Stores list of PointNodes)
    point_nodes: Mapped[list["PointNode"]] = relationship(
        back_populates="tourist_point",
        cascade="all, delete-orphan"
    )


class TouristPointCategory(Base):
    __tablename__ = 'tourist_point_categories'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # 1. The Foreign Key pointing to the parent category by ID
    # If this is NULL, it's a "Top-Level" category (e.g., "Nature")
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tourist_point_categories.id"))
    # 2. Relationships
    tourist_points: Mapped[List["TouristPoint"]] = relationship(
        back_populates="category"
    )
    # children: allows you to do category.sub_categories
    parent: Mapped[Optional["TouristPointCategory"]] = relationship(
        remote_side=[id],
        back_populates="sub_categories"
    )
    # This category could have a lot of sub-categories (list of TouristPointCategory)
    sub_categories: Mapped[List["TouristPointCategory"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan" # when parent is removed, child would be removed also
    )


class Node(Base):
    '''
    Geographic entity in the transportation network.

    Represents any physical location that can be:
    - A source or destination of travel
    - Connected to other nodes via transport segments
    - Located precisely with coordinates

    Philosophy: Nodes are network abstractions. They exist to enable routing
    algorithms to find paths through space. A node doesn't care about cultural
    significance or tourist appeal—it just cares about where it is and what
    connects to it.
    '''
    __tablename__ = "nodes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    type: Mapped[NodeType] = mapped_column(SQLEnum(NodeType))

    # Relationships
    outgoing_segments: Mapped[List["TransportSegment"]] = relationship(
        "TransportSegment",
        foreign_keys="TransportSegment.from_node",
        back_populates="from_node_rel",
    )
    incoming_segments: Mapped[List["TransportSegment"]] = relationship(
        "TransportSegment",
        foreign_keys="TransportSegment.to_node",
        back_populates="to_node_rel",
    )
    # PointNode Related (Stores list of PointNodes)
    point_nodes: Mapped[list["PointNode"]] = relationship(
        back_populates="node",
        cascade="all, delete-orphan"
    )


class TransportSegment(Base):
    __tablename__ = 'transport_segments'
    id: Mapped[int] = mapped_column(primary_key=True)
    from_node: Mapped[int] = mapped_column(ForeignKey("nodes.id")) # Source node would be Almaty
    to_node: Mapped[int] = mapped_column(ForeignKey("nodes.id"))
    transport_mode: Mapped[TransportMode] = mapped_column(SQLEnum(TransportMode))
    distance_km: Mapped[float] = mapped_column(Float)
    time_minutes: Mapped[int] = mapped_column(Integer)
    cost: Mapped[float] = mapped_column(DECIMAL)

    from_node_rel: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[from_node],
        back_populates="outgoing_segments"
    )

    to_node_rel: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[to_node],
        back_populates="incoming_segments"
    )


class PointNode(Base):
    """
       Physical access point connecting a TouristPoint to the transportation network.

       A PointNode represents the "last-mile" location where a traveler transitions
       from the transport network to the actual tourist destination.

       Why this entity exists:
       - TouristPoints are content-driven objects (stories, attractions, experiences)
       - Nodes are abstract elements of the transport graph (cities, stations, airports)
       - A TouristPoint is rarely located directly on a transport node

       The PointNode acts as a bridge between them, answering questions like:
       - Where exactly does a tourist arrive before reaching this destination?
       - What transport node is the closest practical entry point?
       - How difficult, long, or expensive is the final stretch?

       A TouristPoint may have multiple PointNodes, allowing different access routes
       (e.g., summer road vs winter route).

       This model enables accurate routing, travel time estimation, and
       realistic user guidance for the final segment of a journey.
    """
    __tablename__ = 'point_nodes'
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    tourist_point_id: Mapped[int] = mapped_column(
        ForeignKey("tourist_points.id"),
        nullable=False
    )
    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"),
        nullable=False
    )
    # Last-mile metadata
    distance_km: Mapped[float] = mapped_column(Float, nullable=True)
    time_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    access_type: Mapped[AccessType] = mapped_column(
        SQLEnum(AccessType),
        nullable=False,
        doc="How the tourist reaches the point from the node (taxi, walk, shuttle)"
    )
    # Relationships
    tourist_point: Mapped["TouristPoint"] = relationship(
        back_populates="point_nodes"
    )
    node: Mapped["Node"] = relationship(
        back_populates="point_nodes"
    )

