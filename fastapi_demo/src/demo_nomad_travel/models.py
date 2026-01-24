from typing import List, Optional

from slugify import slugify
from sqlalchemy import (
    Integer,
    String,
    ForeignKey,
    Text, Float, Enum as SQLEnum, DECIMAL, event  # to don't confuse it with Python's built-in Enum class
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from enums import NodeType, TransportMode


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

