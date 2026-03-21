"""
Application Configuration
Uses Pydantic Settings for environment-based configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    
    For local development with SQLite, the database_url will default to a local file.
    In production, you would set DATABASE_URL environment variable to PostgreSQL.
    """
    
    # Database — all fields are Optional so SQLite fallback works without .env
    # Database — Optional so SQLite fallback works when .env is absent.
    # pydantic-settings reads .env automatically — no need for os.getenv().
    POSTGRES_USER:     Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_SERVER:   Optional[str] = None
    POSTGRES_PORT:     str            = "5432"
    POSTGRES_DB:       Optional[str] = None
    
    # Application settings
    app_name: str = "Nomad Travel KZ"
    app_version: str = "1.0.0"
    # Security settings
    DEBUG: bool = False  # Set DEBUG=True in .env for local dev only
    SECRET_KEY: str = "change_me_in_production"
    TEAM_API_KEY: str = "dev_team_key"
    ENABLE_ADMIN: bool = False
    ALLOWED_ADMIN_IPS: List[str] = ["127.0.0.1", "localhost"]
    
    root_path: str = ""  # Used when hosting behind a proxy (like Nginx)

    # CORS — comma-separated list of allowed origins.
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:80"]
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"  # Overridden by docker-compose
    
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
        """
        Build the database URL from environment variables.

        If all 4 Postgres credentials are present → use PostgreSQL.
        Otherwise → fall back to SQLite (local development without .env).
        """
        pg_ready = all([
            self.POSTGRES_USER,
            self.POSTGRES_PASSWORD,
            self.POSTGRES_SERVER,
            self.POSTGRES_DB,
        ])
        if pg_ready:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        # Fallback: SQLite for local dev / CI without a running Postgres instance
        return "sqlite+aiosqlite:///./app.db"


# Global settings instance
settings = Settings()
