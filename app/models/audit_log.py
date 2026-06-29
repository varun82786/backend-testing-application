"""AuditLog ORM model.

Provides an immutable, append-only log of all significant domain
events (creates, updates, status changes, payments, etc.).
Old and new values are stored as JSON-encoded text for flexibility.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import AuditAction
from app.database.base import Base


class AuditLog(Base):
    """Immutable audit trail entry.

    Attributes:
        id: Primary key.
        entity: Entity type name (e.g. 'Order', 'Payment').
        entity_id: String representation of the entity's primary key.
        action: The action that was performed.
        old_value: JSON-serialized previous state (nullable for creates).
        new_value: JSON-serialized new state (nullable for deletes).
        performed_by: Username or identifier of the actor.
        timestamp: When the action occurred (server-side default).
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[AuditAction] = mapped_column(nullable=False, index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, entity='{self.entity}', "
            f"entity_id='{self.entity_id}', action={self.action.value})>"
        )
