"""Shipment management API routes.

Provides endpoints for creating shipments, retrieving shipment
details, and updating shipment status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.auth.permissions import RoleChecker
from app.core.enums import UserRole
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.shipment import ShipmentCreate, ShipmentResponse, ShipmentStatusUpdate
from app.services.shipment import ShipmentService

router = APIRouter(prefix="/shipments", tags=["Shipments"])


@router.post(
    "/",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shipment",
    description=(
        "Create a new shipment record for an order. The order must be "
        "in a shippable state (typically Packed or Paid). "
        "Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Order not in shippable state"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_shipment(
    data: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ShipmentResponse:
    """Create a new shipment for an order.

    Args:
        data: Shipment creation payload with order ID, tracking number,
            and carrier.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The newly created shipment record.
    """
    service = ShipmentService(db)
    shipment = service.create_shipment(data, performed_by=current_user.username)
    return ShipmentResponse.model_validate(shipment)


@router.get(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    summary="Get shipment by ID",
    description="Retrieve a single shipment record by its ID. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Shipment not found"},
    },
)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ShipmentResponse:
    """Retrieve a shipment by ID.

    Args:
        shipment_id: The shipment's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The requested shipment record.
    """
    service = ShipmentService(db)
    shipment = service.get_by_id(shipment_id)
    return ShipmentResponse.model_validate(shipment)


@router.get(
    "/order/{order_id}",
    response_model=list[ShipmentResponse],
    summary="Get shipments by order ID",
    description="Retrieve all shipment records for a specific order. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
def get_shipments_by_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ShipmentResponse]:
    """Retrieve all shipments for a given order.

    Args:
        order_id: The order's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        List of shipment records associated with the order.
    """
    service = ShipmentService(db)
    shipments = service.get_by_order_id(order_id)
    return [ShipmentResponse.model_validate(s) for s in shipments]


@router.put(
    "/{shipment_id}/status",
    response_model=ShipmentResponse,
    summary="Update shipment status",
    description=(
        "Transition a shipment to a new status. Only valid transitions "
        "are allowed (e.g., Pending → Packed → Shipped → Delivered). "
        "Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Shipment not found"},
        409: {"model": ErrorResponse, "description": "Invalid status transition"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def update_shipment_status(
    shipment_id: int,
    data: ShipmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ShipmentResponse:
    """Update the status of a shipment.

    Args:
        shipment_id: The shipment's primary key.
        data: New status to transition to.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The shipment with updated status.
    """
    service = ShipmentService(db)
    shipment = service.update_status(
        shipment_id, data.status, performed_by=current_user.username
    )
    return ShipmentResponse.model_validate(shipment)
