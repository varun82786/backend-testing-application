"""Repository for Inventory entity data access."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Inventory
from app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[Inventory]):
    """Repository for ``Inventory`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with inventory-specific queries such as
    lookup by product/warehouse combination, low-stock alerts, and
    out-of-stock detection.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the InventoryRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(Inventory, db)

    def get_by_product_and_warehouse(
        self, product_id: int, warehouse: str
    ) -> Inventory | None:
        """Retrieve inventory for a specific product in a specific warehouse.

        Args:
            product_id: The product's primary key.
            warehouse: The warehouse identifier/name.

        Returns:
            The matching ``Inventory`` instance, or ``None`` if not found.
        """
        stmt = select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.warehouse == warehouse,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_product(self, product_id: int) -> list[Inventory]:
        """Retrieve all inventory records for a given product.

        Args:
            product_id: The product's primary key.

        Returns:
            A list of ``Inventory`` instances across all warehouses.
        """
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_warehouse(
        self, warehouse: str, skip: int = 0, limit: int = 20
    ) -> list[Inventory]:
        """Retrieve a paginated list of inventory records for a warehouse.

        Args:
            warehouse: The warehouse identifier/name.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of ``Inventory`` instances in the specified warehouse.
        """
        stmt = (
            select(Inventory)
            .where(Inventory.warehouse == warehouse)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_low_stock(self, threshold: int = 10) -> list[Inventory]:
        """Retrieve inventory records where quantity is at or below a threshold.

        Useful for triggering reorder alerts.  Records with zero
        quantity are included.

        Args:
            threshold: The stock-level threshold (inclusive).
                Defaults to 10.

        Returns:
            A list of ``Inventory`` instances with low stock.
        """
        stmt = select(Inventory).where(Inventory.quantity <= threshold)
        return list(self.db.execute(stmt).scalars().all())

    def get_out_of_stock(self) -> list[Inventory]:
        """Retrieve inventory records where quantity is zero.

        Returns:
            A list of ``Inventory`` instances that are completely
            out of stock.
        """
        stmt = select(Inventory).where(Inventory.quantity == 0)
        return list(self.db.execute(stmt).scalars().all())
