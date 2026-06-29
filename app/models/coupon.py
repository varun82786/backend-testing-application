"""Coupon ORM model.

Supports both percentage-based and flat-amount discounts.
Single-use coupons are marked as ``used`` after first application.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DiscountType
from app.database.base import Base


class Coupon(Base):
    """Discount coupon that can be applied to an order.

    Attributes:
        id: Primary key.
        code: Unique coupon code (case-insensitive by convention).
        discount_type: PERCENTAGE or FLAT.
        discount_value: Discount amount or percentage.
        minimum_order: Minimum order subtotal required to use the coupon.
        expiry: Coupon expiration datetime.
        active: Whether the coupon is currently active.
        single_use: If True, the coupon can only be used once.
        used: Tracks whether a single-use coupon has been redeemed.
        created_at: Record creation timestamp.
    """

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    discount_type: Mapped[DiscountType] = mapped_column(nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    minimum_order: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    expiry: Mapped[datetime] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    single_use: Mapped[bool] = mapped_column(default=False, nullable=False)
    used: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<Coupon(id={self.id}, code='{self.code}', "
            f"type={self.discount_type.value}, value={self.discount_value})>"
        )
