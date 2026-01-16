from sqlalchemy import (
    Integer,
    String,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Regions(Base):
    __tablename__ = 'regions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False) # Mapped makes convert our datatype to our DB's type (like VarChar 50)
    slug: Mapped[str] = mapped_column(String(50), nullable=True, unique=True)

    tourist_points: Mapped[list['TouristPoints']] = relationship(
        'TouristPoints',
        back_populates='region',
        cascade='all, delete-orphan',
    )


class TouristPoints(Base):
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
    region: Mapped['Regions'] = relationship(
        'Regions',
        back_populates='tourist_points',
    )