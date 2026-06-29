"""Audit log API routes.

Provides a read-only endpoint for querying the immutable audit
trail. Only accessible to Admin users.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.auth.permissions import RoleChecker
from app.core.enums import AuditAction, UserRole
from app.database.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.services.audit import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "/",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="Query audit logs",
    description=(
        "Retrieve a paginated list of audit log entries with optional "
        "filters for entity type, entity ID, action, and actor. "
        "Requires Admin role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    entity: str | None = Query(None, description="Filter by entity type (e.g., 'Order')"),
    entity_id: str | None = Query(None, description="Filter by entity primary key"),
    action: AuditAction | None = Query(None, description="Filter by audit action"),
    performed_by: str | None = Query(None, description="Filter by actor username"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[AuditLogResponse]:
    """Query the audit log with optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        entity: Optional entity type filter.
        entity_id: Optional entity ID filter.
        action: Optional audit action filter.
        performed_by: Optional actor username filter.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Paginated list of audit log entries.
    """
    service = AuditService(db)
    skip = (page - 1) * page_size
    logs = service.get_logs(
        entity=entity,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        skip=skip,
        limit=page_size,
    )
    total = service.count_logs(entity=entity, action=action)
    items = [AuditLogResponse.model_validate(log) for log in logs]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
