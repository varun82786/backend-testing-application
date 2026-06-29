"""Repository for Product entity data access."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Repository for ``Product`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with product-specific queries such as
    SKU lookup, active-product filtering, and free-text search.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the ProductRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(Product, db)

    def get_by_sku(self, sku: str) -> Product | None:
        """Retrieve a product by its unique SKU.

        Args:
            sku: The stock-keeping unit identifier.

        Returns:
            The matching ``Product`` instance, or ``None`` if not found.
        """
        stmt = select(Product).where(Product.sku == sku)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active(self, skip: int = 0, limit: int = 20) -> list[Product]:
        """Retrieve a paginated list of active (non-discontinued) products.

        Args:
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of active ``Product`` instances.
        """
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_active(self) -> int:
        """Return the total number of active products.

        Returns:
            The count of products where ``is_active`` is ``True``.
        """
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.is_active.is_(True))
        )
        return self.db.execute(stmt).scalar_one()

    def search(
        self, query: str, skip: int = 0, limit: int = 20
    ) -> list[Product]:
        """Search products by name or SKU containing the query string.

        Performs a case-insensitive ``LIKE`` search across the
        ``name`` and ``sku`` columns.

        Args:
            query: The search term (partial match).
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of matching ``Product`` instances.
        """
        pattern = f"%{query}%"
        stmt = (
            select(Product)
            .where(
                or_(
                    Product.name.ilike(pattern),
                    Product.sku.ilike(pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
