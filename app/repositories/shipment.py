"""Repository for Shipment entity data access."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Shipment
from app.repositories.base import BaseRepository


class ShipmentRepository(BaseRepository[Shipment]):
    """Repository for ``Shipment`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with shipment-specific queries such as
    lookup by order ID or tracking number.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the ShipmentRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(Shipment, db)

    def get_by_order_id(self, order_id: int) -> Shipment | None:
        """Retrieve the shipment record associated with an order.

        Args:
            order_id: The order's primary key.

        Returns:
            The matching ``Shipment`` instance, or ``None`` if no
            shipment has been created for the order.
        """
        stmt = select(Shipment).where(Shipment.order_id == order_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_tracking_number(self, tracking_number: str) -> Shipment | None:
        """Retrieve a shipment by its carrier tracking number.

        Args:
            tracking_number: The unique tracking number assigned by the
                shipping carrier.

        Returns:
            The matching ``Shipment`` instance, or ``None`` if not found.
        """
        stmt = select(Shipment).where(
            Shipment.tracking_number == tracking_number
        )
        return self.db.execute(stmt).scalar_one_or_none()
