"""Application configuration using Pydantic Settings.

All configuration is loaded from environment variables with sensible defaults.
Use a `.env` file for local development.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_env: Deployment environment (development, staging, production).
        app_host: Host to bind the server to.
        app_port: Port to bind the server to.
        app_debug: Enable debug mode.
        app_title: Application title for OpenAPI docs.
        app_version: Application version for OpenAPI docs.
        database_url: SQLAlchemy database connection string.
        jwt_secret_key: Secret key for JWT token signing.
        jwt_algorithm: Algorithm used for JWT encoding.
        jwt_access_token_expire_minutes: Access token TTL in minutes.
        jwt_refresh_token_expire_days: Refresh token TTL in days.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Log output format ('json' or 'human').
        enable_negative_inventory: Bug flag - allow inventory to go negative.
        enable_duplicate_payment: Bug flag - skip duplicate transaction check.
        enable_wrong_gst: Bug flag - apply incorrect GST calculation.
        enable_skip_audit_log: Bug flag - silently drop audit log entries.
        enable_shipment_without_payment: Bug flag - allow shipping unpaid orders.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True
    app_title: str = "Order Management System"
    app_version: str = "1.0.0"

    # Database
    database_url: str = "sqlite:///./oms.db"

    # JWT Authentication
    jwt_secret_key: str = "change-this-to-a-secure-random-string-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Logging
    log_level: str = "INFO"
    log_format: str = "human"

    # Bug Injection Flags
    enable_negative_inventory: bool = False
    enable_duplicate_payment: bool = False
    enable_wrong_gst: bool = False
    enable_skip_audit_log: bool = False
    enable_shipment_without_payment: bool = False

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings singleton.

    Returns:
        Settings: Application settings instance.
    """
    return Settings()
