"""Generic base repository providing common CRUD operations.

All concrete repositories should inherit from this class.
Repositories never commit — the caller (service layer) manages transactions.
Uses SQLAlchemy 2.x `select()` style queries throughout.
"""

from typing import Generic, TypeVar, Type

from sqlalchemy import select, func
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Generic base repository providing common CRUD operations.

    All concrete repositories should inherit from this class,
    binding the ``ModelT`` type parameter to a specific ORM model.
    Repositories never commit — the caller (service layer) manages
    transactions via ``Session.commit()`` / ``Session.rollback()``.

    Args:
        model: The SQLAlchemy ORM model class this repository manages.
        db: The active SQLAlchemy ``Session`` for database operations.
    """

    def __init__(self, model: Type[ModelT], db: Session) -> None:
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> ModelT | None:
        """Retrieve a single entity by its primary key.

        Args:
            id: The integer primary key of the entity.

        Returns:
            The entity instance if found, otherwise ``None``.
        """
        return self.db.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 20) -> list[ModelT]:
        """Retrieve a paginated list of all entities.

        Args:
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of entity instances.
        """
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        """Return the total number of entities in the table.

        Returns:
            The total row count.
        """
        stmt = select(func.count()).select_from(self.model)
        return self.db.execute(stmt).scalar_one()

    def create(self, entity: ModelT) -> ModelT:
        """Persist a new entity to the session.

        The entity is flushed (to obtain its generated ID) but **not**
        committed.  The caller is responsible for committing the
        transaction.

        Args:
            entity: The ORM model instance to persist.

        Returns:
            The persisted entity with any server-generated defaults populated.
        """
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def update(self, entity: ModelT, update_data: dict) -> ModelT:
        """Update an existing entity with the provided data dictionary.

        Only attributes that already exist on the model are updated;
        unknown keys are silently ignored.  The session is flushed but
        **not** committed.

        Args:
            entity: The ORM model instance to update.
            update_data: A mapping of attribute names to new values.

        Returns:
            The updated entity with refreshed state from the database.
        """
        for key, value in update_data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        """Mark an entity for deletion in the current session.

        The session is flushed but **not** committed.

        Args:
            entity: The ORM model instance to delete.
        """
        self.db.delete(entity)
        self.db.flush()
