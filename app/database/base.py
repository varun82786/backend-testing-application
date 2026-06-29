"""SQLAlchemy declarative base for all ORM models.

All models should inherit from `Base` defined here. This ensures
a single metadata instance is shared across the application,
which is required for Alembic migrations to work correctly.
"""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Provides:
        - Shared metadata for schema generation and migrations.
        - Common configuration inherited by all models.
    """

    pass
