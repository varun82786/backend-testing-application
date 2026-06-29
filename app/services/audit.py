"""Audit logging service.

Provides a thin façade over the ``AuditLogRepository`` for creating
and querying immutable audit trail entries.  All mutating service
methods delegate here so that audit creation is consistent and
centralised.

The ``should_create_audit_log`` bug injector is checked on every
write — when the ``SKIP_AUDIT_LOG`` bug is active, audit entries
are silently suppressed (intentional defect for testing).
"""

from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.bugs.injectors import should_create_audit_log
from app.core.enums import AuditAction
from app.models import AuditLog
from app.repositories.audit_log import AuditLogRepository
from app.utils.helpers import serialize_for_audit


class AuditService:
    """Service for creating and querying audit log entries.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = AuditLogRepository(db)
        self.db = db

    def log(
        self,
        entity: str,
        entity_id: int | str,
        action: AuditAction,
        old_value: Any = None,
        new_value: Any = None,
        performed_by: str | None = None,
    ) -> AuditLog | None:
        """Create an audit log entry.

        Respects the ``SKIP_AUDIT_LOG`` bug flag — when active, the
        entry is silently skipped and ``None`` is returned.

        Args:
            entity: The entity type name (e.g. ``"Order"``).
            entity_id: The entity's primary key (coerced to ``str``).
            action: The ``AuditAction`` that occurred.
            old_value: Previous state (model instance or dict).
            new_value: New state (model instance or dict).
            performed_by: Username of the actor, if known.

        Returns:
            The persisted ``AuditLog`` instance, or ``None`` when
            audit logging is suppressed by the bug flag.
        """
        if not should_create_audit_log():
            logger.warning(
                "Audit log suppressed (SKIP_AUDIT_LOG active) for "
                "{entity}#{entity_id} action={action}",
                entity=entity,
                entity_id=entity_id,
                action=action.value,
            )
            return None

        audit = AuditLog(
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            old_value=serialize_for_audit(old_value),
            new_value=serialize_for_audit(new_value),
            performed_by=performed_by,
        )
        created = self.repo.create(audit)

        logger.info(
            "Audit log created: {entity}#{entity_id} action={action} by={performed_by}",
            entity=entity,
            entity_id=entity_id,
            action=action.value,
            performed_by=performed_by,
        )
        return created

    def get_logs(
        self,
        entity: str | None = None,
        entity_id: str | None = None,
        action: AuditAction | None = None,
        performed_by: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[AuditLog]:
        """Retrieve audit logs with optional filters.

        Filters are combined with AND semantics when multiple are
        provided.

        Args:
            entity: Filter by entity type name.
            entity_id: Filter by entity primary key.
            action: Filter by ``AuditAction``.
            performed_by: Filter by actor username.
            skip: Number of records to skip (offset).
            limit: Maximum records to return.

        Returns:
            A list of matching ``AuditLog`` instances.
        """
        if performed_by is not None:
            return self.repo.get_by_performer(
                performed_by=performed_by, skip=skip, limit=limit
            )

        if action is not None and entity is None:
            return self.repo.get_by_action(
                action=action, skip=skip, limit=limit
            )

        if entity is not None:
            return self.repo.get_by_entity(
                entity=entity,
                entity_id=entity_id,
                skip=skip,
                limit=limit,
            )

        # No filters — return all (paginated).
        return self.repo.get_all(skip=skip, limit=limit)

    def count_logs(
        self,
        entity: str | None = None,
        action: str | None = None,
    ) -> int:
        """Count audit log entries matching optional filters.

        Args:
            entity: Optional entity type name filter.
            action: Optional action string filter.

        Returns:
            The count of matching audit log entries.
        """
        return self.repo.count_filtered(entity=entity, action=action)
