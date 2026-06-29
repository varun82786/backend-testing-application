"""Customer ORM model.

Represents end-customers who place orders. Each customer can have
multiple orders and accumulates loyalty points.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


class Customer(Base):
    """Customer entity in the order management system.

    Attributes:
        id: Primary key.
        name: Full name of the customer.
        email: Unique email address.
        phone: Unique phone number.
        address: Optional shipping/billing address.
        loyalty_points: Accumulated reward points.
        created_at: Row creation timestamp.
        updated_at: Last modification timestamp.
        orders: Related orders placed by this customer.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    loyalty_points: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────
    orders: Mapped[list[Order]] = relationship(
        "Order", back_populates="customer", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}', email='{self.email}')>"
