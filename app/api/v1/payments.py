"""Payment processing API routes.

Provides endpoints for processing payments, retrieving payment
details, and issuing refunds.
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
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Process a payment",
    description=(
        "Record and process a payment for an existing order. Validates "
        "the order exists, is in a payable state, and the amount matches. "
        "Accessible to all authenticated users."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        402: {"model": ErrorResponse, "description": "Payment processing failed"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Duplicate transaction reference"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def process_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaymentResponse:
    """Process a payment for an order.

    Args:
        data: Payment creation payload with order ID, method,
            transaction reference, and amount.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The processed payment record.
    """
    service = PaymentService(db)
    payment = service.process_payment(data, performed_by=current_user.username)
    return PaymentResponse.model_validate(payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment by ID",
    description="Retrieve a single payment record by its ID. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Payment not found"},
    },
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaymentResponse:
    """Retrieve a payment by ID.

    Args:
        payment_id: The payment's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The requested payment record.
    """
    service = PaymentService(db)
    payment = service.get_by_id(payment_id)
    return PaymentResponse.model_validate(payment)


@router.get(
    "/order/{order_id}",
    response_model=list[PaymentResponse],
    summary="Get payments by order ID",
    description="Retrieve all payment records for a specific order. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
def get_payments_by_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[PaymentResponse]:
    """Retrieve all payments for a given order.

    Args:
        order_id: The order's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        List of payment records associated with the order.
    """
    service = PaymentService(db)
    payments = service.get_by_order_id(order_id)
    return [PaymentResponse.model_validate(p) for p in payments]


@router.post(
    "/{payment_id}/refund",
    response_model=PaymentResponse,
    summary="Refund a payment",
    description=(
        "Issue a refund for a previously successful payment. "
        "Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        402: {"model": ErrorResponse, "description": "Refund processing failed"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Payment not found"},
        409: {"model": ErrorResponse, "description": "Payment cannot be refunded"},
    },
)
def refund_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaymentResponse:
    """Refund a payment.

    Args:
        payment_id: The payment's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The updated payment record with refunded status.
    """
    service = PaymentService(db)
    payment = service.refund(payment_id, performed_by=current_user.username)
    return PaymentResponse.model_validate(payment)
