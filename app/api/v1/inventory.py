"""Inventory management API routes.

Provides endpoints for creating, listing, retrieving, and updating
warehouse inventory records with optional product and warehouse filters.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.auth.permissions import RoleChecker
from app.core.enums import UserRole
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.inventory import InventoryCreate, InventoryResponse, InventoryUpdate
from app.services.inventory import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post(
    "/",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an inventory record",
    description=(
        "Create a new inventory record linking a product to a warehouse "
        "with initial stock quantities. Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Product not found"},
        409: {"model": ErrorResponse, "description": "Duplicate product-warehouse combination"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_inventory(
    data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> InventoryResponse:
    """Create a new inventory record.

    Args:
        data: Inventory creation payload.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The newly created inventory record.
    """
    service = InventoryService(db)
    inventory = service.create(data, performed_by=current_user.username)
    return InventoryResponse.model_validate(inventory)


@router.get(
    "/",
    response_model=PaginatedResponse[InventoryResponse],
    summary="List inventory records",
    description=(
        "Retrieve a paginated list of inventory records. Optionally filter "
        "by product ID or warehouse name. Accessible to all authenticated users."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def list_inventory(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    product_id: int | None = Query(None, description="Filter by product ID"),
    warehouse: str | None = Query(None, description="Filter by warehouse name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[InventoryResponse]:
    """Retrieve a paginated list of inventory records.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        product_id: Optional product ID filter.
        warehouse: Optional warehouse name filter.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Paginated list of inventory records.
    """
    service = InventoryService(db)
    items, total = service.get_all(
        page=page,
        page_size=page_size,
        product_id=product_id,
        warehouse=warehouse,
    )
    inv_items = [InventoryResponse.model_validate(i) for i in items]
    return PaginatedResponse.create(
        items=inv_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{inventory_id}",
    response_model=InventoryResponse,
    summary="Get inventory record by ID",
    description="Retrieve a single inventory record by its ID. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Inventory record not found"},
    },
)
def get_inventory(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> InventoryResponse:
    """Retrieve an inventory record by ID.

    Args:
        inventory_id: The inventory record's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The requested inventory record.
    """
    service = InventoryService(db)
    inventory = service.get_by_id(inventory_id)
    return InventoryResponse.model_validate(inventory)


@router.put(
    "/{inventory_id}",
    response_model=InventoryResponse,
    summary="Update an inventory record",
    description="Update stock quantities for an inventory record. Requires Admin or Manager role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Inventory record not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def update_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> InventoryResponse:
    """Update an inventory record.

    Args:
        inventory_id: The inventory record's primary key.
        data: Fields to update.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The updated inventory record.
    """
    service = InventoryService(db)
    inventory = service.update(inventory_id, data, performed_by=current_user.username)
    return InventoryResponse.model_validate(inventory)
