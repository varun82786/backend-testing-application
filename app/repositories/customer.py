"""Repository for Customer entity data access."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository for ``Customer`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with customer-specific queries such as
    lookup by email/phone and free-text search across name and email.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the CustomerRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(Customer, db)

    def get_by_email(self, email: str) -> Customer | None:
        """Retrieve a customer by their unique email address.

        Args:
            email: The email address to search for.

        Returns:
            The matching ``Customer`` instance, or ``None`` if not found.
        """
        stmt = select(Customer).where(Customer.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_phone(self, phone: str) -> Customer | None:
        """Retrieve a customer by their phone number.

        Args:
            phone: The phone number to search for.

        Returns:
            The matching ``Customer`` instance, or ``None`` if not found.
        """
        stmt = select(Customer).where(Customer.phone == phone)
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self, query: str, skip: int = 0, limit: int = 20
    ) -> list[Customer]:
        """Search customers by name or email containing the query string.

        Performs a case-insensitive ``LIKE`` search across the
        ``name`` and ``email`` columns.

        Args:
            query: The search term (partial match).
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of matching ``Customer`` instances.
        """
        pattern = f"%{query}%"
        stmt = (
            select(Customer)
            .where(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.email.ilike(pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
