from typing import List, Optional

from sqlalchemy import (
    Integer,
    String,
    ForeignKey,
    Text, Float, Enum as SQLEnum # to don't confuse it with Python's built-in Enum class
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.demo_nomad_travel.enums import NodeType


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = 'regions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False) # Mapped makes convert our datatype to our DB's type (like VarChar 50)
    slug: Mapped[str] = mapped_column(String(50), nullable=True, unique=True)

    tourist_points: Mapped[list['TouristPoint']] = relationship(
        'TouristPoints',
        back_populates='region',
        cascade='all, delete-orphan',
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
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    # If type == tourist_point: Tourist Point object would be created
    type: Mapped[NodeType] = mapped_column(SQLEnum(NodeType))

    # Link to the "User Info"
    tourist_point: Mapped[Optional["TouristPoint"]] = relationship(back_populates="node")


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

    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('regions.id'),
    )
    region: Mapped['Region'] = relationship(
        'Regions',
        back_populates='tourist_points',
    )

    category: Mapped['TouristPointCategory'] = relationship(
        'TouristPointCategory', back_populates='tourist_points',)

class TouristPointCategory(Base):
    __tablename__ = 'tourist_point_categories'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=True, unique=True)

    # 1. The Foreign Key pointing to the parent category
    # If this is NULL, it's a "Top-Level" category (e.g., "Nature")
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    # 2. Relationships
    # children: allows you to do category.sub_categories
    sub_categories: Mapped[List["TouristPointCategory"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan" # when parent is removed, child would be removed also
    )