"""Inventory Pydantic schemas.

Provides create, update, and response schemas for warehouse
inventory management.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryCreate(BaseModel):
    """Payload for creating an inventory record.

    Attributes:
        product_id: Foreign key to the product.
        warehouse: Warehouse or location identifier.
        quantity: Initial on-hand quantity (>= 0).
        reserved_quantity: Initially reserved quantity (defaults to 0).
    """

    product_id: int = Field(gt=0, description="Product FK")
    warehouse: str = Field(
        min_length=1, max_length=100, description="Warehouse identifier"
    )
    quantity: int = Field(ge=0, description="On-hand quantity")
    reserved_quantity: int = Field(
        default=0, ge=0, description="Reserved quantity"
    )


class InventoryUpdate(BaseModel):
    """Payload for partially updating an inventory record.

    Attributes:
        quantity: Updated on-hand quantity.
        reserved_quantity: Updated reserved quantity.
    """

    quantity: int | None = Field(default=None, ge=0, description="On-hand quantity")
    reserved_quantity: int | None = Field(
        default=None, ge=0, description="Reserved quantity"
    )


class InventoryResponse(BaseModel):
    """Serialized inventory record for API responses.

    Attributes:
        id: Primary key.
        product_id: Associated product.
        warehouse: Warehouse identifier.
        quantity: Current on-hand stock.
        reserved_quantity: Currently reserved stock.
        updated_at: Last stock update timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse: str
    quantity: int
    reserved_quantity: int
    updated_at: datetime
