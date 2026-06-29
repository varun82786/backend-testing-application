"""Order management API routes.

Provides endpoints for creating, listing, retrieving, and managing
orders including status transitions and cancellation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.auth.permissions import RoleChecker
from app.core.enums import OrderStatus, UserRole
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    description=(
        "Place a new order with one or more line items. Validates product "
        "availability, calculates pricing with GST and optional coupon "
        "discount. Accessible to all authenticated users."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Customer or product not found"},
        409: {"model": ErrorResponse, "description": "Insufficient stock or invalid coupon"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Create a new order.

    Args:
        data: Order creation payload with customer ID, line items,
            and optional coupon code.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The newly created order with computed totals.
    """
    service = OrderService(db)
    order = service.create_order(data, performed_by=current_user.username)
    return OrderResponse.model_validate(order)


@router.get(
    "/",
    response_model=PaginatedResponse[OrderResponse],
    summary="List all orders",
    description=(
        "Retrieve a paginated list of orders. Optionally filter by status "
        "or customer ID. Accessible to all authenticated users."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def list_orders(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: OrderStatus | None = Query(
        None, alias="status", description="Filter by order status"
    ),
    customer_id: int | None = Query(None, description="Filter by customer ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[OrderResponse]:
    """Retrieve a paginated list of orders.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        status_filter: Optional order status filter.
        customer_id: Optional customer ID filter.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Paginated list of orders.
    """
    service = OrderService(db)
    items, total = service.get_all(
        page=page,
        page_size=page_size,
        status=status_filter,
        customer_id=customer_id,
    )
    order_items = [OrderResponse.model_validate(o) for o in items]
    return PaginatedResponse.create(
        items=order_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
    description="Retrieve a single order with all line items. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Retrieve an order by ID.

    Args:
        order_id: The order's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The requested order with line items.
    """
    service = OrderService(db)
    order = service.get_by_id(order_id)
    return OrderResponse.model_validate(order)


@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
    description=(
        "Transition an order to a new status. Only valid transitions are "
        "allowed (e.g., Pending → Paid). Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Invalid status transition"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Update the status of an order.

    Args:
        order_id: The order's primary key.
        data: New status to transition to.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The order with updated status.
    """
    service = OrderService(db)
    order = service.update_status(
        order_id, data.status, performed_by=current_user.username
    )
    return OrderResponse.model_validate(order)


@router.delete(
    "/{order_id}",
    response_model=SuccessResponse,
    summary="Cancel an order",
    description=(
        "Cancel an order. Only non-terminal orders can be cancelled. "
        "Requires Admin role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Order cannot be cancelled"},
    },
)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse:
    """Cancel an order.

    Args:
        order_id: The order's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Success confirmation message.
    """
    service = OrderService(db)
    service.cancel_order(order_id, performed_by=current_user.username)
    return SuccessResponse(message=f"Order {order_id} cancelled successfully")
