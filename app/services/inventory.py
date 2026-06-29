"""Inventory management service.

Provides CRUD plus the three stock lifecycle operations:

* **reserve_stock** — holds stock for a pending order.
* **release_stock** — returns reserved stock (cancellation / payment
  failure).
* **deduct_stock** — converts a reservation to an actual quantity
  decrease (delivery confirmation).

Respects the ``NEGATIVE_INVENTORY`` bug flag: when active, the
available-stock check is skipped, allowing reservations that would
drive stock negative.
"""

from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.orm import Session

from app.bugs.injectors import should_check_stock_negative
from app.core.enums import AuditAction
from app.exceptions.base import (
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
    InsufficientStockError,
)
from app.models import Inventory
from app.repositories.inventory import InventoryRepository
from app.repositories.product import ProductRepository
from app.schemas.inventory import InventoryCreate, InventoryUpdate
from app.services.audit import AuditService
from app.utils.helpers import model_to_dict


class InventoryService:
    """Service for warehouse inventory operations.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = InventoryRepository(db)
        self.product_repo = ProductRepository(db)
        self.audit_service = AuditService(db)
        self.db = db

    # ── CRUD ───────────────────────────────────────────────────────

    def create(
        self,
        data: InventoryCreate,
        performed_by: str | None = None,
    ) -> Inventory:
        """Create an inventory record for a product in a warehouse.

        Validates that the referenced product exists and that the
        product/warehouse combination is not already tracked.

        Args:
            data: Validated inventory creation payload.
            performed_by: Username of the actor.

        Returns:
            The newly created ``Inventory`` instance.

        Raises:
            EntityNotFoundError: If the product does not exist.
            ConflictError: If the product/warehouse pair already exists.
        """
        product = self.product_repo.get_by_id(data.product_id)
        if not product:
            raise EntityNotFoundError("Product", data.product_id)

        existing = self.repo.get_by_product_and_warehouse(
            data.product_id, data.warehouse
        )
        if existing:
            raise ConflictError(
                message=(
                    f"Inventory for product {data.product_id} in warehouse "
                    f"'{data.warehouse}' already exists"
                ),
                details={
                    "product_id": data.product_id,
                    "warehouse": data.warehouse,
                },
            )

        inventory = Inventory(
            product_id=data.product_id,
            warehouse=data.warehouse,
            quantity=data.quantity,
            reserved_quantity=data.reserved_quantity,
        )
        created = self.repo.create(inventory)

        logger.info(
            "Inventory created: id={id} product={product_id} warehouse={warehouse}",
            id=created.id,
            product_id=created.product_id,
            warehouse=created.warehouse,
        )

        self.audit_service.log(
            entity="Inventory",
            entity_id=created.id,
            action=AuditAction.CREATED,
            new_value=created,
            performed_by=performed_by,
        )

        return created

    def get_by_id(self, id: int) -> Inventory:
        """Retrieve an inventory record by primary key.

        Args:
            id: The inventory record's primary key.

        Returns:
            The ``Inventory`` instance.

        Raises:
            EntityNotFoundError: If no record exists with the given ID.
        """
        inv = self.repo.get_by_id(id)
        if not inv:
            raise EntityNotFoundError("Inventory", id)
        return inv

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        product_id: int | None = None,
        warehouse: str | None = None,
    ) -> tuple[list[Inventory], int]:
        """Retrieve a paginated list of inventory records.

        Supports optional filtering by product or warehouse.

        Args:
            page: 1-based page number.
            page_size: Records per page.
            product_id: Optional product filter.
            warehouse: Optional warehouse filter.

        Returns:
            A tuple of ``(items, total_count)``.
        """
        skip = (page - 1) * page_size

        if product_id is not None:
            items = self.repo.get_by_product(product_id)
            total = len(items)
            # Apply manual pagination on the filtered result.
            items = items[skip : skip + page_size]
        elif warehouse is not None:
            items = self.repo.get_by_warehouse(
                warehouse, skip=skip, limit=page_size
            )
            total = len(
                self.repo.get_by_warehouse(warehouse, skip=0, limit=999999)
            )
        else:
            items = self.repo.get_all(skip=skip, limit=page_size)
            total = self.repo.count()

        return items, total

    def update(
        self,
        id: int,
        data: InventoryUpdate,
        performed_by: str | None = None,
    ) -> Inventory:
        """Update an inventory record.

        Args:
            id: The inventory record's primary key.
            data: Validated partial-update payload.
            performed_by: Username of the actor.

        Returns:
            The updated ``Inventory`` instance.

        Raises:
            EntityNotFoundError: If the record does not exist.
        """
        inventory = self.get_by_id(id)
        old_values = model_to_dict(inventory)

        update_data = data.model_dump(exclude_unset=True)
        updated = self.repo.update(inventory, update_data)

        logger.info("Inventory updated: id={id}", id=id)

        self.audit_service.log(
            entity="Inventory",
            entity_id=id,
            action=AuditAction.UPDATED,
            old_value=old_values,
            new_value=updated,
            performed_by=performed_by,
        )

        return updated

    # ── Stock Lifecycle Operations ─────────────────────────────────

    def reserve_stock(self, product_id: int, quantity: int) -> Inventory:
        """Reserve stock for an order.

        Scans all warehouses for the product and selects the *first*
        warehouse with sufficient available stock (``quantity −
        reserved_quantity``).

        When the ``NEGATIVE_INVENTORY`` bug is active, the
        available-stock check is bypassed — reservations that would
        drive available stock below zero are allowed.

        Args:
            product_id: The product whose stock should be reserved.
            quantity: Number of units to reserve.

        Returns:
            The updated ``Inventory`` instance in the chosen warehouse.

        Raises:
            InsufficientStockError: If no single warehouse has enough
                available stock (and the bug flag is not active).
        """
        inventories = self.repo.get_by_product(product_id)

        if not inventories:
            product = self.product_repo.get_by_id(product_id)
            sku = product.sku if product else "UNKNOWN"
            raise InsufficientStockError(
                product_id=product_id,
                sku=sku,
                warehouse="N/A",
                requested=quantity,
                available=0,
            )

        for inv in inventories:
            available = inv.quantity - inv.reserved_quantity

            if should_check_stock_negative():
                # Normal mode: enforce that available >= requested.
                if available >= quantity:
                    old_values = model_to_dict(inv)
                    self.repo.update(
                        inv, {"reserved_quantity": inv.reserved_quantity + quantity}
                    )
                    logger.info(
                        "Stock reserved: product={product_id} qty={qty} "
                        "warehouse={warehouse}",
                        product_id=product_id,
                        qty=quantity,
                        warehouse=inv.warehouse,
                    )
                    self.audit_service.log(
                        entity="Inventory",
                        entity_id=inv.id,
                        action=AuditAction.STOCK_RESERVED,
                        old_value=old_values,
                        new_value=inv,
                    )
                    return inv
            else:
                # Bug mode: skip the availability check — allow
                # negative available stock.
                old_values = model_to_dict(inv)
                self.repo.update(
                    inv, {"reserved_quantity": inv.reserved_quantity + quantity}
                )
                logger.warning(
                    "Stock reserved (NEGATIVE_INVENTORY active): "
                    "product={product_id} qty={qty} warehouse={warehouse}",
                    product_id=product_id,
                    qty=quantity,
                    warehouse=inv.warehouse,
                )
                self.audit_service.log(
                    entity="Inventory",
                    entity_id=inv.id,
                    action=AuditAction.STOCK_RESERVED,
                    old_value=old_values,
                    new_value=inv,
                )
                return inv

        # No warehouse had sufficient stock.
        best = max(inventories, key=lambda i: i.quantity - i.reserved_quantity)
        product = self.product_repo.get_by_id(product_id)
        sku = product.sku if product else "UNKNOWN"
        raise InsufficientStockError(
            product_id=product_id,
            sku=sku,
            warehouse=best.warehouse,
            requested=quantity,
            available=best.quantity - best.reserved_quantity,
        )

    def release_stock(self, product_id: int, quantity: int) -> None:
        """Release previously reserved stock.

        Used on order cancellation or payment failure to return
        reserved units back to the available pool.  The release is
        applied to the *first* warehouse that has enough reserved
        quantity.

        Args:
            product_id: The product whose reservation to release.
            quantity: Number of units to release.
        """
        inventories = self.repo.get_by_product(product_id)
        remaining = quantity

        for inv in inventories:
            if remaining <= 0:
                break

            releasable = min(inv.reserved_quantity, remaining)
            if releasable > 0:
                old_values = model_to_dict(inv)
                self.repo.update(
                    inv,
                    {"reserved_quantity": inv.reserved_quantity - releasable},
                )
                remaining -= releasable

                logger.info(
                    "Stock released: product={product_id} qty={qty} "
                    "warehouse={warehouse}",
                    product_id=product_id,
                    qty=releasable,
                    warehouse=inv.warehouse,
                )
                self.audit_service.log(
                    entity="Inventory",
                    entity_id=inv.id,
                    action=AuditAction.STOCK_RELEASED,
                    old_value=old_values,
                    new_value=inv,
                )

    def deduct_stock(self, product_id: int, quantity: int) -> None:
        """Convert reserved stock to an actual quantity deduction.

        Called upon delivery confirmation — reduces both ``quantity``
        and ``reserved_quantity`` by the delivered amount across the
        product's warehouses.

        Args:
            product_id: The product whose stock to deduct.
            quantity: Number of units to deduct.
        """
        inventories = self.repo.get_by_product(product_id)
        remaining = quantity

        for inv in inventories:
            if remaining <= 0:
                break

            deductible = min(inv.reserved_quantity, remaining)
            if deductible > 0:
                old_values = model_to_dict(inv)
                self.repo.update(
                    inv,
                    {
                        "quantity": inv.quantity - deductible,
                        "reserved_quantity": inv.reserved_quantity - deductible,
                    },
                )
                remaining -= deductible

                logger.info(
                    "Stock deducted: product={product_id} qty={qty} "
                    "warehouse={warehouse}",
                    product_id=product_id,
                    qty=deductible,
                    warehouse=inv.warehouse,
                )
                self.audit_service.log(
                    entity="Inventory",
                    entity_id=inv.id,
                    action=AuditAction.STOCK_DEDUCTED,
                    old_value=old_values,
                    new_value=inv,
                )
