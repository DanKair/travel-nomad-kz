"""
Database Configuration and Session Management

This module sets up SQLAlchemy 2.x with:
- Engine creation
- Session factory for dependency injection
- DeclarativeBase for all models
- Database initialization
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# Create SQLAlchemy engine
# For SQLite: check_same_thread=False allows FastAPI to use the same connection across threads
# For production PostgreSQL, you'd use a connection pool instead
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.debug  # Log SQL queries in debug mode
)

# Session factory for creating database sessions
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    All models will inherit from this class to get SQLAlchemy ORM functionality.
    Using DeclarativeBase is the modern SQLAlchemy 2.x approach.
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to inject database sessions.
    
    Usage in FastAPI endpoints:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    
    This ensures:
    - Each request gets its own database session
    - Session is automatically closed after request
    - Proper transaction handling
    """
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


async def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This should be called when the application starts.
    It creates all tables defined by models inheriting from Base.
    """
    # Import all models here to ensure they're registered with Base
    from app import models  # noqa: F401
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized successfully")
