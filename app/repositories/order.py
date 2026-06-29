"""Repository for Order entity data access."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import OrderStatus
from app.models import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Repository for ``Order`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with order-specific queries including
    eager loading of related ``OrderItem`` and ``Customer`` entities,
    status-based filtering, and customer-scoped lookups.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the OrderRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(Order, db)

    def get_by_id_with_items(self, id: int) -> Order | None:
        """Retrieve an order with eagerly loaded items and customer.

        Uses ``selectinload`` for the one-to-many ``items`` relationship
        and ``joinedload`` for the many-to-one ``customer`` relationship
        to avoid N+1 query issues.

        Args:
            id: The order's primary key.

        Returns:
            The ``Order`` instance with loaded relationships, or
            ``None`` if not found.
        """
        stmt = (
            select(Order)
            .where(Order.id == id)
            .options(
                selectinload(Order.items),
                joinedload(Order.customer),
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_customer(
        self, customer_id: int, skip: int = 0, limit: int = 20
    ) -> list[Order]:
        """Retrieve a paginated list of orders for a specific customer.

        Args:
            customer_id: The customer's primary key.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of ``Order`` instances belonging to the customer.
        """
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_status(
        self, status: OrderStatus, skip: int = 0, limit: int = 20
    ) -> list[Order]:
        """Retrieve a paginated list of orders filtered by status.

        Args:
            status: The ``OrderStatus`` value to filter on.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of ``Order`` instances matching the given status.
        """
        stmt = (
            select(Order)
            .where(Order.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_status(self, status: OrderStatus) -> int:
        """Return the total number of orders with a specific status.

        Args:
            status: The ``OrderStatus`` value to count.

        Returns:
            The count of orders matching the status.
        """
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.status == status)
        )
        return self.db.execute(stmt).scalar_one()

    def get_all_with_items(
        self, skip: int = 0, limit: int = 20
    ) -> list[Order]:
        """Retrieve a paginated list of orders with eagerly loaded items.

        Similar to ``get_all`` but uses ``selectinload`` for items and
        ``joinedload`` for customer to avoid N+1 queries when iterating
        over results.

        Args:
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of ``Order`` instances with loaded relationships.
        """
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                joinedload(Order.customer),
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())
