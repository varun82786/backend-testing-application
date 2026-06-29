"""Payment Pydantic schemas.

Covers payment creation, response serialization, and refund
request / response schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    """Payload for recording a new payment against an order.

    Attributes:
        order_id: The order being paid.
        method: Payment method used.
        transaction_reference: External gateway reference (unique).
        amount: Payment amount (must be > 0).
    """

    order_id: int = Field(gt=0, description="Order FK")
    method: PaymentMethod = Field(description="Payment method")
    transaction_reference: str = Field(
        min_length=1, max_length=255, description="Unique gateway reference"
    )
    amount: Decimal = Field(
        gt=0, max_digits=12, decimal_places=2, description="Payment amount"
    )


class PaymentResponse(BaseModel):
    """Serialized payment for API responses.

    Attributes:
        id: Primary key.
        order_id: Associated order.
        status: Current payment status.
        method: Payment method used.
        transaction_reference: Gateway reference.
        amount: Payment amount.
        created_at: Payment timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    status: PaymentStatus
    method: PaymentMethod
    transaction_reference: str
    amount: Decimal
    created_at: datetime


class RefundRequest(BaseModel):
    """Payload for initiating a payment refund.

    Attributes:
        reason: Optional reason for the refund.
    """

    reason: str | None = Field(
        default=None, max_length=500, description="Refund reason"
    )


class RefundResponse(BaseModel):
    """Response after a refund has been processed.

    Attributes:
        payment: The updated payment record (status = REFUNDED).
        message: Human-readable confirmation message.
    """

    model_config = ConfigDict(from_attributes=True)

    payment: PaymentResponse
    message: str = Field(
        default="Refund processed successfully",
        description="Confirmation message",
    )
