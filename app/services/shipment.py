"""Shipment management service.

Handles shipment creation and status tracking.  On delivery
confirmation the service deducts stock (converting reservations to
actual quantity reductions) via ``InventoryService``.

Bug injection points:
    * ``should_check_payment_before_shipment`` — when the
      ``SHIPMENT_WITHOUT_PAYMENT`` bug is active, shipments can be
      created for unpaid orders.
"""

from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.orm import Session

from app.bugs.injectors import should_check_payment_before_shipment
from app.core.enums import (
    AuditAction,
    OrderStatus,
    PaymentStatus,
    ShipmentStatus,
)
from app.exceptions.base import (
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
    InvalidStateTransitionError,
)
from app.models import Shipment
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.repositories.shipment import ShipmentRepository
from app.schemas.shipment import ShipmentCreate
from app.services.audit import AuditService
from app.services.inventory import InventoryService
from app.utils.helpers import model_to_dict


class ShipmentService:
    """Service for shipment lifecycle operations.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = ShipmentRepository(db)
        self.order_repo = OrderRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.inventory_service = InventoryService(db)
        self.audit_service = AuditService(db)
        self.db = db

    def create_shipment(
        self,
        data: ShipmentCreate,
        performed_by: str | None = None,
    ) -> Shipment:
        """Create a shipment for an order.

        Workflow:
            1. Validate the order exists.
            2. Check the order is ``PAID`` or ``PACKED`` (respects the
               ``SHIPMENT_WITHOUT_PAYMENT`` bug flag).
            3. Check no existing shipment for this order.
            4. Check for duplicate tracking number.
            5. Create the shipment.
            6. Write an audit log entry.

        Args:
            data: Validated shipment creation payload.
            performed_by: Username of the actor.

        Returns:
            The newly created ``Shipment`` instance.

        Raises:
            EntityNotFoundError: If the order does not exist.
            BusinessValidationError: If the order is not in an
                acceptable status for shipping.
            ConflictError: If a shipment already exists for the order
                or the tracking number is a duplicate.
        """
        # 1. Validate order exists.
        order = self.order_repo.get_by_id_with_items(data.order_id)
        if not order:
            raise EntityNotFoundError("Order", data.order_id)

        # 2. Check order status — payment must have been made.
        if should_check_payment_before_shipment():
            allowed_statuses = {OrderStatus.PAID, OrderStatus.PACKED}
            if order.status not in allowed_statuses:
                raise BusinessValidationError(
                    message=(
                        f"Cannot create shipment for order in "
                        f"'{order.status.value}' status — order must be "
                        f"PAID or PACKED"
                    ),
                    details={
                        "order_id": data.order_id,
                        "order_status": order.status.value,
                    },
                )
        else:
            logger.warning(
                "Payment-before-shipment check skipped "
                "(SHIPMENT_WITHOUT_PAYMENT bug active) for order={order_id}",
                order_id=data.order_id,
            )

        # 3. Check no existing shipment.
        existing = self.repo.get_by_order_id(data.order_id)
        if existing:
            raise ConflictError(
                message=f"Shipment already exists for order {data.order_id}",
                details={
                    "order_id": data.order_id,
                    "existing_shipment_id": existing.id,
                },
            )

        # 4. Check duplicate tracking number.
        if self.repo.get_by_tracking_number(data.tracking_number):
            raise ConflictError(
                message=(
                    f"Tracking number '{data.tracking_number}' is already "
                    f"in use"
                ),
                details={"tracking_number": data.tracking_number},
            )

        # 5. Create shipment.
        shipment = Shipment(
            order_id=data.order_id,
            tracking_number=data.tracking_number,
            carrier=data.carrier,
            status=ShipmentStatus.PENDING,
        )
        created = self.repo.create(shipment)

        logger.info(
            "Shipment created: id={id} order={order_id} tracking={tracking}",
            id=created.id,
            order_id=data.order_id,
            tracking=data.tracking_number,
        )

        # 6. Audit log.
        self.audit_service.log(
            entity="Shipment",
            entity_id=created.id,
            action=AuditAction.CREATED,
            new_value=created,
            performed_by=performed_by,
        )

        return created

    def get_by_id(self, id: int) -> Shipment:
        """Retrieve a shipment by primary key.

        Args:
            id: The shipment's primary key.

        Returns:
            The ``Shipment`` instance.

        Raises:
            EntityNotFoundError: If no shipment exists with the given ID.
        """
        shipment = self.repo.get_by_id(id)
        if not shipment:
            raise EntityNotFoundError("Shipment", id)
        return shipment

    def get_by_order_id(self, order_id: int) -> Shipment:
        """Retrieve the shipment associated with an order.

        Args:
            order_id: The order's primary key.

        Returns:
            The ``Shipment`` instance.

        Raises:
            EntityNotFoundError: If no shipment exists for the order.
        """
        shipment = self.repo.get_by_order_id(order_id)
        if not shipment:
            raise EntityNotFoundError("Shipment", f"order_id={order_id}")
        return shipment

    def update_status(
        self,
        id: int,
        new_status: ShipmentStatus,
        performed_by: str | None = None,
    ) -> Shipment:
        """Update the status of a shipment.

        Status transitions are validated against
        ``ShipmentStatus.can_transition_to``.

        Side effects by target status:
            * ``SHIPPED`` — sets ``shipped_at`` and updates the order
              status to ``SHIPPED``.
            * ``DELIVERED`` — sets ``delivered_at``, updates the order
              status to ``DELIVERED``, and deducts stock for every
              order item (converting reservations to actual quantity
              decreases).

        Args:
            id: The shipment's primary key.
            new_status: The target ``ShipmentStatus``.
            performed_by: Username of the actor.

        Returns:
            The updated ``Shipment`` instance.

        Raises:
            EntityNotFoundError: If the shipment does not exist.
            InvalidStateTransitionError: If the transition is not
                allowed by the state machine.
        """
        shipment = self.get_by_id(id)
        old_status = shipment.status

        if not old_status.can_transition_to(new_status):
            raise InvalidStateTransitionError(
                entity="Shipment",
                current_status=old_status.value,
                target_status=new_status.value,
            )

        old_values = model_to_dict(shipment)
        now = datetime.now(timezone.utc)

        update_data: dict = {"status": new_status}

        if new_status == ShipmentStatus.SHIPPED:
            update_data["shipped_at"] = now

            # Update order status to SHIPPED.
            order = self.order_repo.get_by_id_with_items(shipment.order_id)
            if order:
                self.order_repo.update(order, {"status": OrderStatus.SHIPPED})

        elif new_status == ShipmentStatus.DELIVERED:
            update_data["delivered_at"] = now

            # Update order status to DELIVERED.
            order = self.order_repo.get_by_id_with_items(shipment.order_id)
            if order:
                self.order_repo.update(order, {"status": OrderStatus.DELIVERED})

                # Deduct stock — convert reservations to actual deductions.
                for item in order.items:
                    self.inventory_service.deduct_stock(
                        product_id=item.product_id, quantity=item.quantity
                    )

        self.repo.update(shipment, update_data)

        logger.info(
            "Shipment status updated: id={id} {old} → {new}",
            id=id,
            old=old_status.value,
            new=new_status.value,
        )

        self.audit_service.log(
            entity="Shipment",
            entity_id=id,
            action=AuditAction.STATUS_CHANGED,
            old_value=old_values,
            new_value=shipment,
            performed_by=performed_by,
        )

        return shipment
