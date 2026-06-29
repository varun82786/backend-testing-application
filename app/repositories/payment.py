"""Repository for Payment entity data access."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Repository for ``Payment`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with payment-specific queries such as
    lookup by order ID or transaction reference.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the PaymentRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(Payment, db)

    def get_by_order_id(self, order_id: int) -> Payment | None:
        """Retrieve the payment record associated with an order.

        Args:
            order_id: The order's primary key.

        Returns:
            The matching ``Payment`` instance, or ``None`` if no payment
            has been recorded for the order.
        """
        stmt = select(Payment).where(Payment.order_id == order_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_transaction_reference(self, ref: str) -> Payment | None:
        """Retrieve a payment by its external transaction reference.

        Args:
            ref: The unique transaction reference string (e.g. from a
                payment gateway).

        Returns:
            The matching ``Payment`` instance, or ``None`` if not found.
        """
        stmt = select(Payment).where(Payment.transaction_reference == ref)
        return self.db.execute(stmt).scalar_one_or_none()
