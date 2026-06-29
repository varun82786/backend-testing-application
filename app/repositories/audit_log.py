"""Repository for AuditLog entity data access."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.models import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for ``AuditLog`` entity CRUD and query operations.

    Extends ``BaseRepository`` with audit-specific queries such as
    filtering by entity type, action, and performer.  Audit logs are
    typically append-only; update and delete operations are inherited
    but generally should not be used in production.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the AuditLogRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(AuditLog, db)

    def get_by_entity(
        self,
        entity: str,
        entity_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[AuditLog]:
        """Retrieve audit logs for a given entity type, optionally by ID.

        Args:
            entity: The entity type name (e.g. ``"Order"``, ``"Product"``).
            entity_id: Optional specific entity ID to narrow the filter.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of ``AuditLog`` instances matching the criteria,
            ordered newest-first.
        """
        stmt = select(AuditLog).where(AuditLog.entity == entity)
        if entity_id is not None:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        stmt = (
            stmt.order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_action(
        self, action: AuditAction, skip: int = 0, limit: int = 20
    ) -> list[AuditLog]:
        """Retrieve audit logs filtered by action type.

        Args:
            action: The ``AuditAction`` enum value to filter on.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of ``AuditLog`` instances matching the action,
            ordered newest-first.
        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_performer(
        self, performed_by: str, skip: int = 0, limit: int = 20
    ) -> list[AuditLog]:
        """Retrieve audit logs for actions performed by a specific user.

        Args:
            performed_by: The username or identifier of the user who
                performed the actions.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of ``AuditLog`` instances for the performer,
            ordered newest-first.
        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.performed_by == performed_by)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_filtered(
        self,
        entity: str | None = None,
        action: str | None = None,
    ) -> int:
        """Return the count of audit logs matching optional filters.

        Both filters are optional; when neither is provided, returns
        the total count of all audit log entries.

        Args:
            entity: Optional entity type name to filter on.
            action: Optional action string to filter on.

        Returns:
            The number of audit log entries matching the criteria.
        """
        stmt = select(func.count()).select_from(AuditLog)
        if entity is not None:
            stmt = stmt.where(AuditLog.entity == entity)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        return self.db.execute(stmt).scalar_one()
