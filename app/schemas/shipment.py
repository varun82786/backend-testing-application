"""Shipment Pydantic schemas.

Covers shipment creation, status updates, and full response
serialization.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ShipmentStatus


class ShipmentCreate(BaseModel):
    """Payload for creating a shipment record.

    Attributes:
        order_id: The order being shipped.
        tracking_number: Carrier-assigned tracking ID.
        carrier: Shipping carrier name.
    """

    order_id: int = Field(gt=0, description="Order FK")
    tracking_number: str = Field(
        min_length=1, max_length=100, description="Carrier tracking number"
    )
    carrier: str = Field(
        min_length=1, max_length=100, description="Carrier name"
    )


class ShipmentStatusUpdate(BaseModel):
    """Payload for updating a shipment's status.

    Attributes:
        status: Target shipment status.
    """

    status: ShipmentStatus = Field(description="New shipment status")


class ShipmentResponse(BaseModel):
    """Serialized shipment for API responses.

    Attributes:
        id: Primary key.
        order_id: Associated order.
        tracking_number: Carrier tracking ID.
        carrier: Carrier name.
        status: Current shipment status.
        shipped_at: Dispatch timestamp.
        delivered_at: Delivery timestamp.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    tracking_number: str
    carrier: str
    status: ShipmentStatus
    shipped_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
