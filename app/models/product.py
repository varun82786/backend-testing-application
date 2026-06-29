"""Product ORM model.

Represents catalogue items that can be ordered. Each product has a
unique SKU, a price, and an associated GST percentage.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.inventory import Inventory
    from app.models.order import OrderItem


class Product(Base):
    """Catalogue product available for purchase.

    Attributes:
        id: Primary key.
        sku: Stock-keeping unit — unique product identifier.
        name: Human-readable product name.
        description: Optional long description.
        price: Unit price exclusive of tax.
        gst_percentage: Applicable GST rate (e.g. 18.00 for 18 %).
        active: Whether the product is currently available for sale.
        created_at: Row creation timestamp.
        updated_at: Last modification timestamp.
        inventory_items: Inventory records across warehouses.
        order_items: Line items referencing this product.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    gst_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────
    inventory_items: Mapped[list[Inventory]] = relationship(
        "Inventory", back_populates="product", lazy="selectin"
    )
    order_items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="product", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}')>"
