"""FastAPI application entry point.

Creates and configures the FastAPI application with middleware,
exception handlers, routes, and database initialisation.
"""

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.database.base import Base
from app.database.session import engine
from app.exceptions.handlers import register_exception_handlers
from app.logging.setup import setup_logging
from app.middleware.logging import RequestLoggingMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Performs the following setup in order:
        1. Load application settings.
        2. Configure Loguru-based structured logging.
        3. Instantiate the FastAPI app with OpenAPI metadata.
        4. Register request logging middleware.
        5. Register domain and validation exception handlers.
        6. Mount the versioned API router.
        7. Add a health-check endpoint.
        8. Register a startup event to create database tables.

    Returns:
        The fully configured FastAPI application instance.
    """
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description="Production-grade Order Management System API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Routes
    app.include_router(api_v1_router)

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """Return application health status.

        Returns:
            Dictionary with status and version information.
        """
        return {"status": "healthy", "version": settings.app_version}

    @app.on_event("startup")
    def on_startup() -> None:
        """Initialise the database on application startup.

        Imports all ORM models to ensure they are registered with
        SQLAlchemy metadata, then creates any missing tables.
        """
        # Import all models to register them with Base.metadata
        import app.models  # noqa: F401

        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
