"""Order and OrderItem Pydantic schemas.

Covers order creation (with nested line items), status updates,
and fully-serialized order responses.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import OrderStatus


# ── OrderItem Schemas ──────────────────────────────────────────────


class OrderItemCreate(BaseModel):
    """Single line item within an order creation request.

    Attributes:
        product_id: Product to order.
        quantity: Number of units (>= 1).
    """

    product_id: int = Field(gt=0, description="Product FK")
    quantity: int = Field(ge=1, description="Units to order")


class OrderItemResponse(BaseModel):
    """Serialized order line item.

    Attributes:
        id: Primary key.
        order_id: Parent order FK.
        product_id: Product FK.
        quantity: Units ordered.
        unit_price: Price per unit at time of order.
        total_price: Computed line total.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    total_price: Decimal


# ── Order Schemas ──────────────────────────────────────────────────


class OrderCreate(BaseModel):
    """Payload for creating a new order.

    Attributes:
        customer_id: Customer placing the order.
        items: At least one line item.
        coupon_code: Optional discount coupon code.
    """

    customer_id: int = Field(gt=0, description="Customer FK")
    items: list[OrderItemCreate] = Field(
        min_length=1, description="Order line items (min 1)"
    )
    coupon_code: str | None = Field(
        default=None, max_length=50, description="Optional coupon code"
    )

    @model_validator(mode="after")
    def validate_unique_products(self) -> OrderCreate:
        """Ensure no duplicate product IDs in a single order."""
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Duplicate product IDs are not allowed in a single order")
        return self


class OrderStatusUpdate(BaseModel):
    """Payload for updating an order's status.

    Attributes:
        status: Target order status.
    """

    status: OrderStatus = Field(description="New order status")


class OrderResponse(BaseModel):
    """Fully serialized order for API responses.

    Attributes:
        id: Primary key.
        customer_id: Customer FK.
        status: Current lifecycle status.
        subtotal: Sum of line-item totals.
        tax: Calculated GST amount.
        discount: Applied discount.
        total: Final payable amount.
        coupon_code: Applied coupon code (if any).
        created_at: Order creation timestamp.
        updated_at: Last update timestamp.
        items: Nested list of line items.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: OrderStatus
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    coupon_code: str | None
    created_at: datetime
    updated_at: datetime | None
    items: list[OrderItemResponse] = Field(default_factory=list)
