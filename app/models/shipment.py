"""Shipment ORM model.

Tracks the physical delivery of an order. Each order has at most one
shipment record, created once the order is packed and ready.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ShipmentStatus
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


class Shipment(Base):
    """Shipment tracking record linked one-to-one with an order.

    Attributes:
        id: Primary key.
        order_id: Foreign key to the order (unique — one shipment per order).
        tracking_number: Carrier-assigned tracking identifier.
        carrier: Shipping carrier name (e.g. 'FedEx', 'BlueDart').
        status: Current shipment lifecycle status.
        shipped_at: Timestamp when the shipment was dispatched.
        delivered_at: Timestamp when the shipment was delivered.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        order: Related order entity.
    """

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), unique=True, nullable=False, index=True
    )
    tracking_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    carrier: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ShipmentStatus] = mapped_column(
        default=ShipmentStatus.PENDING, nullable=False
    )
    shipped_at: Mapped[datetime | None] = mapped_column(nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────
    order: Mapped[Order] = relationship(
        "Order", back_populates="shipment", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Shipment(id={self.id}, order_id={self.order_id}, "
            f"tracking='{self.tracking_number}', status={self.status.value})>"
        )
