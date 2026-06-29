"""Database session management.

Provides the SQLAlchemy engine, session factory, and a FastAPI
dependency for obtaining database sessions with automatic
commit/rollback semantics.
"""

from collections.abc import Generator

from sqlalchemy import event, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _create_engine():
    """Create the SQLAlchemy engine based on application settings.

    For SQLite, enables foreign key enforcement and WAL journal mode
    for better concurrency. For other databases, uses standard settings.

    Returns:
        Engine: Configured SQLAlchemy engine.
    """
    settings = get_settings()
    connect_args = {}

    # SQLite-specific configuration
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=settings.app_debug and settings.is_development,
        pool_pre_ping=True,
    )

    # Enable SQLite foreign keys and WAL mode on every connection
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = _create_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session.

    Yields a session that automatically commits on success or
    rolls back on exception. The session is always closed after use.

    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
