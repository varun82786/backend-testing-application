"""Product catalogue management service.

Provides CRUD operations for the product catalogue with:

* Duplicate SKU detection on create and update.
* Price-positivity validation.
* Soft-delete semantics (``active = False``) instead of hard delete.
* Optional ``active_only`` filtering on list operations.
* Full audit trail for every mutation.
"""

from loguru import logger
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.exceptions.base import (
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
)
from app.models import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.audit import AuditService
from app.utils.helpers import model_to_dict


class ProductService:
    """Service for product lifecycle operations.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = ProductRepository(db)
        self.audit_service = AuditService(db)
        self.db = db

    def create(
        self,
        data: ProductCreate,
        performed_by: str | None = None,
    ) -> Product:
        """Create a new product in the catalogue.

        Validates that the SKU is unique and that the price is
        strictly positive.

        Args:
            data: Validated product creation payload.
            performed_by: Username of the actor, if known.

        Returns:
            The newly created ``Product`` instance.

        Raises:
            ConflictError: If the SKU is already in use.
            BusinessValidationError: If the price is not positive.
        """
        if self.repo.get_by_sku(data.sku):
            raise ConflictError(
                message=f"Product with SKU '{data.sku}' already exists",
                details={"field": "sku", "value": data.sku},
            )

        if data.price <= 0:
            raise BusinessValidationError(
                message="Product price must be greater than zero",
                details={"field": "price", "value": str(data.price)},
            )

        product = Product(
            sku=data.sku,
            name=data.name,
            description=data.description,
            price=data.price,
            gst_percentage=data.gst_percentage,
            active=data.active,
        )
        created = self.repo.create(product)

        logger.info(
            "Product created: id={id} sku={sku}",
            id=created.id,
            sku=created.sku,
        )

        self.audit_service.log(
            entity="Product",
            entity_id=created.id,
            action=AuditAction.CREATED,
            new_value=created,
            performed_by=performed_by,
        )

        return created

    def get_by_id(self, id: int) -> Product:
        """Retrieve a product by primary key.

        Args:
            id: The product's primary key.

        Returns:
            The ``Product`` instance.

        Raises:
            EntityNotFoundError: If no product exists with the given ID.
        """
        product = self.repo.get_by_id(id)
        if not product:
            raise EntityNotFoundError("Product", id)
        return product

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        active_only: bool = False,
    ) -> tuple[list[Product], int]:
        """Retrieve a paginated list of products with total count.

        When ``active_only`` is ``True``, only products with
        ``active = True`` are included.

        Args:
            page: 1-based page number.
            page_size: Number of records per page.
            active_only: Whether to exclude soft-deleted products.

        Returns:
            A tuple of ``(items, total_count)``.
        """
        skip = (page - 1) * page_size

        if active_only:
            items = self.repo.get_active(skip=skip, limit=page_size)
            total = self.repo.count_active()
        else:
            items = self.repo.get_all(skip=skip, limit=page_size)
            total = self.repo.count()

        return items, total

    def update(
        self,
        id: int,
        data: ProductUpdate,
        performed_by: str | None = None,
    ) -> Product:
        """Update an existing product.

        Only fields present in *data* (non-``None``) are applied.
        If the SKU would change (via a hypothetical update), uniqueness
        is re-validated.

        Args:
            id: The product's primary key.
            data: Validated partial-update payload.
            performed_by: Username of the actor.

        Returns:
            The updated ``Product`` instance.

        Raises:
            EntityNotFoundError: If the product does not exist.
            ConflictError: If the new SKU collides with another product.
        """
        product = self.get_by_id(id)
        old_values = model_to_dict(product)

        update_data = data.model_dump(exclude_unset=True)

        # Re-validate SKU uniqueness if it were to change.
        # Note: ProductUpdate does not expose ``sku`` in the schema,
        # but we guard defensively in case the schema evolves.
        if "sku" in update_data and update_data["sku"] != product.sku:
            existing = self.repo.get_by_sku(update_data["sku"])
            if existing and existing.id != id:
                raise ConflictError(
                    message=f"Product with SKU '{update_data['sku']}' already exists",
                    details={"field": "sku", "value": update_data["sku"]},
                )

        updated = self.repo.update(product, update_data)

        logger.info("Product updated: id={id}", id=id)

        self.audit_service.log(
            entity="Product",
            entity_id=id,
            action=AuditAction.UPDATED,
            old_value=old_values,
            new_value=updated,
            performed_by=performed_by,
        )

        return updated

    def delete(
        self,
        id: int,
        performed_by: str | None = None,
    ) -> None:
        """Soft-delete a product by setting ``active = False``.

        The product is not physically removed — it is marked as
        inactive so that existing order history remains consistent.

        Args:
            id: The product's primary key.
            performed_by: Username of the actor.

        Raises:
            EntityNotFoundError: If the product does not exist.
        """
        product = self.get_by_id(id)
        old_values = model_to_dict(product)

        self.repo.update(product, {"active": False})

        logger.info("Product soft-deleted: id={id}", id=id)

        self.audit_service.log(
            entity="Product",
            entity_id=id,
            action=AuditAction.DELETED,
            old_value=old_values,
            new_value=product,
            performed_by=performed_by,
        )
