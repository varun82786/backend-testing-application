"""Order and OrderItem ORM models.

An Order belongs to a Customer and contains one or more OrderItems.
Financial fields (subtotal, tax, discount, total) are stored as
fixed-precision decimals to avoid floating-point rounding issues.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderStatus
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.payment import Payment
    from app.models.product import Product
    from app.models.shipment import Shipment


class Order(Base):
    """A customer order with financial summary and status tracking.

    Attributes:
        id: Primary key.
        customer_id: Foreign key to the placing customer.
        status: Current lifecycle status.
        subtotal: Sum of line-item totals before tax / discount.
        tax: Calculated GST amount.
        discount: Applied discount amount.
        total: Final payable amount (subtotal + tax − discount).
        coupon_code: Optional coupon code applied to the order.
        created_at: Order creation timestamp.
        updated_at: Last modification timestamp.
        customer: Related customer entity.
        items: Line items in this order.
        payment: Associated payment (one-to-one).
        shipment: Associated shipment (one-to-one).
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        default=OrderStatus.PENDING, nullable=False
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────
    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="orders", lazy="selectin"
    )
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    payment: Mapped[Payment | None] = relationship(
        "Payment", back_populates="order", uselist=False, lazy="selectin"
    )
    shipment: Mapped[Shipment | None] = relationship(
        "Shipment", back_populates="order", uselist=False, lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, customer_id={self.customer_id}, "
            f"status={self.status.value}, total={self.total})>"
        )


class OrderItem(Base):
    """Line item within an order.

    Attributes:
        id: Primary key.
        order_id: Foreign key to the parent order (cascade delete).
        product_id: Foreign key to the ordered product.
        quantity: Number of units ordered.
        unit_price: Price per unit at the time of ordering.
        total_price: quantity × unit_price (pre-computed for reporting).
        order: Parent order.
        product: Related product.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # ── Relationships ──────────────────────────────────────────────
    order: Mapped[Order] = relationship(
        "Order", back_populates="items", lazy="selectin"
    )
    product: Mapped[Product] = relationship(
        "Product", back_populates="order_items", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<OrderItem(id={self.id}, order_id={self.order_id}, "
            f"product_id={self.product_id}, qty={self.quantity})>"
        )
