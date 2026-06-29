"""Payment processing service.

Handles payment creation (with validation against the order state
machine) and refund processing (with order cancellation and stock
release).

Bug injection points:
    * ``should_check_duplicate_payment`` — when the
      ``DUPLICATE_PAYMENT`` bug is active, duplicate transaction
      reference validation is skipped.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.bugs.injectors import should_check_duplicate_payment
from app.core.enums import AuditAction, OrderStatus, PaymentStatus
from app.exceptions.base import (
    ConflictError,
    EntityNotFoundError,
    InvalidStateTransitionError,
    PaymentError,
)
from app.models import Payment
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.services.audit import AuditService
from app.services.inventory import InventoryService
from app.schemas.payment import PaymentCreate
from app.utils.helpers import model_to_dict


class PaymentService:
    """Service for payment processing operations.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = PaymentRepository(db)
        self.order_repo = OrderRepository(db)
        self.inventory_service = InventoryService(db)
        self.audit_service = AuditService(db)
        self.db = db

    def process_payment(
        self,
        data: PaymentCreate,
        performed_by: str | None = None,
    ) -> Payment:
        """Process a payment for an order.

        Workflow:
            1. Validate the order exists and is in ``PENDING`` status.
            2. Check no existing successful payment for this order.
            3. Validate the payment amount matches the order total.
            4. Check for duplicate ``transaction_reference`` (respects
               the ``DUPLICATE_PAYMENT`` bug flag).
            5. Create the ``Payment`` with ``status = SUCCESS``.
            6. Transition the order to ``PAID``.
            7. Write an audit log entry.

        Args:
            data: Validated payment creation payload.
            performed_by: Username of the actor.

        Returns:
            The newly created ``Payment`` instance.

        Raises:
            EntityNotFoundError: If the order does not exist.
            InvalidStateTransitionError: If the order is not in
                ``PENDING`` status.
            ConflictError: If a successful payment already exists for
                this order, or if the transaction reference is a
                duplicate.
            PaymentError: If the payment amount does not match the
                order total.
        """
        # 1. Validate order exists and is PENDING.
        order = self.order_repo.get_by_id_with_items(data.order_id)
        if not order:
            raise EntityNotFoundError("Order", data.order_id)

        if order.status != OrderStatus.PENDING:
            raise InvalidStateTransitionError(
                entity="Order",
                current_status=order.status.value,
                target_status="paid",
            )

        # 2. Check for existing successful payment.
        existing_payment = self.repo.get_by_order_id(data.order_id)
        if existing_payment and existing_payment.status == PaymentStatus.SUCCESS:
            raise ConflictError(
                message=f"Order {data.order_id} already has a successful payment",
                details={"order_id": data.order_id, "payment_id": existing_payment.id},
            )

        # 3. Validate payment amount matches order total.
        if data.amount != order.total:
            raise PaymentError(
                message=(
                    f"Payment amount {data.amount} does not match "
                    f"order total {order.total}"
                ),
                details={
                    "payment_amount": str(data.amount),
                    "order_total": str(order.total),
                },
            )

        # 4. Check duplicate transaction reference.
        if should_check_duplicate_payment():
            existing_ref = self.repo.get_by_transaction_reference(
                data.transaction_reference
            )
            if existing_ref:
                raise ConflictError(
                    message=(
                        f"Transaction reference '{data.transaction_reference}' "
                        f"has already been used"
                    ),
                    details={
                        "transaction_reference": data.transaction_reference,
                        "existing_payment_id": existing_ref.id,
                    },
                )
        else:
            logger.warning(
                "Duplicate payment check skipped (DUPLICATE_PAYMENT bug active) "
                "for ref={ref}",
                ref=data.transaction_reference,
            )

        # 5. Create payment with SUCCESS status.
        payment = Payment(
            order_id=data.order_id,
            status=PaymentStatus.SUCCESS,
            method=data.method,
            transaction_reference=data.transaction_reference,
            amount=data.amount,
        )
        created_payment = self.repo.create(payment)

        # 6. Update order status to PAID.
        self.order_repo.update(order, {"status": OrderStatus.PAID})

        logger.info(
            "Payment processed: id={id} order={order_id} amount={amount}",
            id=created_payment.id,
            order_id=data.order_id,
            amount=data.amount,
        )

        # 7. Audit log.
        self.audit_service.log(
            entity="Payment",
            entity_id=created_payment.id,
            action=AuditAction.PAYMENT_PROCESSED,
            new_value=created_payment,
            performed_by=performed_by,
        )

        return created_payment

    def get_by_id(self, id: int) -> Payment:
        """Retrieve a payment by primary key.

        Args:
            id: The payment's primary key.

        Returns:
            The ``Payment`` instance.

        Raises:
            EntityNotFoundError: If no payment exists with the given ID.
        """
        payment = self.repo.get_by_id(id)
        if not payment:
            raise EntityNotFoundError("Payment", id)
        return payment

    def get_by_order_id(self, order_id: int) -> Payment:
        """Retrieve the payment associated with an order.

        Args:
            order_id: The order's primary key.

        Returns:
            The ``Payment`` instance.

        Raises:
            EntityNotFoundError: If no payment exists for the order.
        """
        payment = self.repo.get_by_order_id(order_id)
        if not payment:
            raise EntityNotFoundError("Payment", f"order_id={order_id}")
        return payment

    def refund(
        self,
        payment_id: int,
        performed_by: str | None = None,
    ) -> Payment:
        """Refund a successful payment.

        Workflow:
            1. Validate the payment exists and has ``SUCCESS`` status.
            2. Update the payment status to ``REFUNDED``.
            3. Transition the order to ``CANCELLED``.
            4. Release reserved stock for all order items.
            5. Write an audit log entry.

        Args:
            payment_id: The payment's primary key.
            performed_by: Username of the actor.

        Returns:
            The updated ``Payment`` instance with ``REFUNDED`` status.

        Raises:
            EntityNotFoundError: If the payment does not exist.
            InvalidStateTransitionError: If the payment is not in
                ``SUCCESS`` status.
        """
        # 1. Validate payment.
        payment = self.get_by_id(payment_id)

        if payment.status != PaymentStatus.SUCCESS:
            raise InvalidStateTransitionError(
                entity="Payment",
                current_status=payment.status.value,
                target_status=PaymentStatus.REFUNDED.value,
            )

        old_values = model_to_dict(payment)

        # 2. Update payment status.
        self.repo.update(payment, {"status": PaymentStatus.REFUNDED})

        # 3. Update order status to CANCELLED.
        order = self.order_repo.get_by_id_with_items(payment.order_id)
        if order:
            self.order_repo.update(order, {"status": OrderStatus.CANCELLED})

            # 4. Release stock.
            for item in order.items:
                self.inventory_service.release_stock(
                    product_id=item.product_id, quantity=item.quantity
                )

        logger.info(
            "Payment refunded: id={id} order={order_id}",
            id=payment_id,
            order_id=payment.order_id,
        )

        # 5. Audit log.
        self.audit_service.log(
            entity="Payment",
            entity_id=payment_id,
            action=AuditAction.PAYMENT_REFUNDED,
            old_value=old_values,
            new_value=payment,
            performed_by=performed_by,
        )

        return payment
