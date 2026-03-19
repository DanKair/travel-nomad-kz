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
# For production PostgreSQL, we use a connection pool to manage concurrent requests
engine_args = {
    "echo": settings.DEBUG,
}

if "sqlite" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL pooling settings
    engine_args.update({
        "pool_size": 10,          # Standard number of persistent connections to keep open
        "max_overflow": 20,       # Max additional connections to create during traffic spikes
        "pool_pre_ping": True,    # Verifies connection is alive before using it (prevents "server closed connection" errors)
        "pool_recycle": 1800,     # Recycle connections every 30 mins to avoid stale connections
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_args)

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
