"""Coupon Pydantic schemas.

Covers coupon creation, update, and response serialization.
Includes business validations for percentage-type coupons.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import DiscountType


class CouponCreate(BaseModel):
    """Payload for creating a new coupon.

    Attributes:
        code: Unique coupon code.
        discount_type: PERCENTAGE or FLAT.
        discount_value: Discount amount or percentage (must be > 0).
        minimum_order: Minimum order subtotal required.
        expiry: Coupon expiration datetime.
        active: Whether the coupon is immediately active.
        single_use: Whether the coupon is single-use.
    """

    code: str = Field(min_length=1, max_length=50, description="Unique coupon code")
    discount_type: DiscountType = Field(description="PERCENTAGE or FLAT")
    discount_value: Decimal = Field(
        gt=0, max_digits=10, decimal_places=2, description="Discount amount/percentage"
    )
    minimum_order: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Minimum order subtotal",
    )
    expiry: datetime = Field(description="Coupon expiration datetime")
    active: bool = Field(default=True, description="Coupon is active")
    single_use: bool = Field(default=False, description="Single-use coupon")

    @model_validator(mode="after")
    def validate_percentage_cap(self) -> CouponCreate:
        """Ensure percentage discounts do not exceed 100 %."""
        if (
            self.discount_type == DiscountType.PERCENTAGE
            and self.discount_value > Decimal("100.00")
        ):
            raise ValueError("Percentage discount cannot exceed 100")
        return self


class CouponUpdate(BaseModel):
    """Payload for partially updating an existing coupon.

    All fields are optional — only provided fields are updated.

    Attributes:
        discount_type: Updated discount type.
        discount_value: Updated discount amount/percentage.
        minimum_order: Updated minimum order subtotal.
        expiry: Updated expiration datetime.
        active: Updated active flag.
        single_use: Updated single-use flag.
    """

    discount_type: DiscountType | None = Field(default=None)
    discount_value: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    minimum_order: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    expiry: datetime | None = Field(default=None)
    active: bool | None = Field(default=None)
    single_use: bool | None = Field(default=None)


class CouponResponse(BaseModel):
    """Serialized coupon for API responses.

    Attributes:
        id: Primary key.
        code: Coupon code.
        discount_type: Discount type.
        discount_value: Discount amount/percentage.
        minimum_order: Minimum order subtotal required.
        expiry: Expiration datetime.
        active: Active flag.
        single_use: Single-use flag.
        used: Whether the coupon has been redeemed.
        created_at: Creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    minimum_order: Decimal
    expiry: datetime
    active: bool
    single_use: bool
    used: bool
    created_at: datetime
