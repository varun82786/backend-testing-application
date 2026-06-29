"""Product Pydantic schemas.

Provides create, update, and response schemas for product catalogue
management endpoints.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    """Payload for creating a new product.

    Attributes:
        sku: Unique stock-keeping unit code.
        name: Product name (1-200 characters).
        description: Optional long description.
        price: Unit price (must be > 0).
        gst_percentage: GST rate (must be >= 0).
        active: Whether the product is available for sale.
    """

    sku: str = Field(min_length=1, max_length=50, description="Unique SKU code")
    name: str = Field(min_length=1, max_length=200, description="Product name")
    description: str | None = Field(
        default=None, max_length=1000, description="Product description"
    )
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2, description="Unit price")
    gst_percentage: Decimal = Field(
        ge=0, max_digits=5, decimal_places=2, description="GST rate (e.g. 18.00)"
    )
    active: bool = Field(default=True, description="Available for sale")

    @field_validator("sku")
    @classmethod
    def sku_uppercase(cls, v: str) -> str:
        """Normalize SKU to uppercase and strip whitespace."""
        return v.strip().upper()


class ProductUpdate(BaseModel):
    """Payload for partially updating an existing product.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated product name.
        description: Updated description.
        price: Updated price (must be > 0 if provided).
        gst_percentage: Updated GST rate.
        active: Updated availability flag.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    gst_percentage: Decimal | None = Field(
        default=None, ge=0, max_digits=5, decimal_places=2
    )
    active: bool | None = Field(default=None)


class ProductResponse(BaseModel):
    """Serialized product for API responses.

    Attributes:
        id: Primary key.
        sku: Stock-keeping unit code.
        name: Product name.
        description: Product description.
        price: Unit price.
        gst_percentage: GST rate.
        active: Availability flag.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    gst_percentage: Decimal
    active: bool
    created_at: datetime
    updated_at: datetime | None
