"""
Database Configuration and Session Management

This module sets up SQLAlchemy 2.x with:
- Engine creation
- Session factory for dependency injection
- DeclarativeBase for all models
- Database initialization
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config import settings


# Create SQLAlchemy engine
# For SQLite: check_same_thread=False allows FastAPI to use the same connection across threads
# For production PostgreSQL, you'd use a connection pool instead
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug  # Log SQL queries in debug mode
)

# Session factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    All models will inherit from this class to get SQLAlchemy ORM functionality.
    Using DeclarativeBase is the modern SQLAlchemy 2.x approach.
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to inject database sessions.
    
    Usage in FastAPI endpoints:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    
    This ensures:
    - Each request gets its own database session
    - Session is automatically closed after request
    - Proper transaction handling
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This should be called when the application starts.
    It creates all tables defined by models inheriting from Base.
    """
    # Import all models here to ensure they're registered with Base
    from app import models  # noqa: F401
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")
