"""Inventory ORM model.

Tracks stock levels per product per warehouse. The reserved_quantity
field supports optimistic locking during order processing — stock is
reserved first, then deducted on shipment.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Inventory(Base):
    """Warehouse inventory record for a single product.

    Attributes:
        id: Primary key.
        product_id: Foreign key to the product.
        warehouse: Warehouse or location identifier.
        quantity: Total on-hand quantity.
        reserved_quantity: Quantity reserved by pending orders.
        updated_at: Last modification timestamp.
        product: Related product entity.
    """

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse", name="uq_inventory_product_warehouse"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    warehouse: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────
    product: Mapped[Product] = relationship(
        "Product", back_populates="inventory_items", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Inventory(id={self.id}, product_id={self.product_id}, "
            f"warehouse='{self.warehouse}', qty={self.quantity})>"
        )
