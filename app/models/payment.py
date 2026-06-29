"""Payment ORM model.

Each order has at most one payment. The transaction_reference is a
unique external identifier (e.g. from a payment gateway).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PaymentMethod, PaymentStatus
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


class Payment(Base):
    """Payment record linked one-to-one with an order.

    Attributes:
        id: Primary key.
        order_id: Foreign key to the order (unique — one payment per order).
        status: Current payment processing status.
        method: Payment method used.
        transaction_reference: External gateway reference (unique).
        amount: Payment amount in the order's currency.
        created_at: Payment creation timestamp.
        order: Related order entity.
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), unique=True, nullable=False, index=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        default=PaymentStatus.PENDING, nullable=False
    )
    method: Mapped[PaymentMethod] = mapped_column(nullable=False)
    transaction_reference: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────
    order: Mapped[Order] = relationship(
        "Order", back_populates="payment", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Payment(id={self.id}, order_id={self.order_id}, "
            f"status={self.status.value}, amount={self.amount})>"
        )
