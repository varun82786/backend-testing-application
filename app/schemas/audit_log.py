"""Audit log Pydantic schemas.

Provides a read-only response schema and a query-filter schema
for the immutable audit trail.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AuditAction


class AuditLogResponse(BaseModel):
    """Serialized audit log entry for API responses.

    Attributes:
        id: Primary key.
        entity: Entity type name (e.g. 'Order').
        entity_id: Entity primary key (as string).
        action: The action that was performed.
        old_value: JSON-serialized previous state.
        new_value: JSON-serialized new state.
        performed_by: Actor who performed the action.
        timestamp: When the action occurred.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity: str
    entity_id: str
    action: AuditAction
    old_value: str | None
    new_value: str | None
    performed_by: str | None
    timestamp: datetime


class AuditLogQuery(BaseModel):
    """Filter parameters for querying audit logs.

    All fields are optional — omitted fields are not filtered.

    Attributes:
        entity: Filter by entity type.
        entity_id: Filter by entity primary key.
        action: Filter by audit action.
        performed_by: Filter by actor.
    """

    entity: str | None = Field(default=None, max_length=50, description="Entity type filter")
    entity_id: str | None = Field(
        default=None, max_length=50, description="Entity ID filter"
    )
    action: AuditAction | None = Field(default=None, description="Action filter")
    performed_by: str | None = Field(
        default=None, max_length=100, description="Actor filter"
    )
