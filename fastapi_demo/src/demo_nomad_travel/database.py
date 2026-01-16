from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Using an in-memory SQLite database for this example.
# /// is used for sqlite, and ./nomad_travel.db means it will create nomad_travel.db file in this directory
DATABASE_URL = "sqlite:///./nomad_travel.db"

engine = create_engine(DATABASE_URL, echo=True)

# SessionLocal is the factory for creating new Session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    """
    Creates the database and all tables defined in the models.
    """
    print("Creating database and tables...")
    Base.metadata.create_all(bind=engine)
    print("Database and tables created.")

# Creates all tables and DB itself
Base.metadata.create_all(bind=engine)

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
