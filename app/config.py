"""
Application Configuration
Uses Pydantic Settings for environment-based configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    
    For local development with SQLite, the database_url will default to a local file.
    In production, you would set DATABASE_URL environment variable to PostgreSQL.
    """
    
    # Database configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "nomad_travel_db")
    
    # Application settings
    app_name: str = "Nomad Travel API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Routing algorithm default weights (can be overridden in API requests)
    # These control the importance of each criterion in route calculation
    default_time_weight: float = 0.4      # 40% importance on travel time
    default_cost_weight: float = 0.3      # 30% importance on cost
    default_comfort_weight: float = 0.2   # 20% importance on comfort
    default_co2_weight: float = 0.1       # 10% importance on environmental impact
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def DATABASE_URL(self) -> str:
        # SQLAlchemy 1.4+ uses postgresql+psycopg2:// instead of postgres://
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


# Global settings instance
settings = Settings()
