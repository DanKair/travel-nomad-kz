"""
Application Configuration
Uses Pydantic Settings for environment-based configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    
    For local development with SQLite, the database_url will default to a local file.
    In production, you would set DATABASE_URL environment variable to PostgreSQL.
    """
    
    # Database configuration
    database_url: str = "sqlite:///./kazakhstan_routes.db"
    
    # Application settings
    app_name: str = "Kazakhstan Tourism Routing API"
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


# Global settings instance
settings = Settings()
