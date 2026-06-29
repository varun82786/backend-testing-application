"""Order management service — the core orchestrator.

Coordinates customer validation, product lookup, inventory
reservation, coupon application, GST calculation, and order /
order-item persistence in a single transactional workflow.

The ``create_order`` method is the most complex operation in the
system: it touches Products, Inventory, Coupons, Orders, and
OrderItems within a single session.  On failure after stock has
been reserved, reservations are explicitly released before the
exception propagates (the session rollback in ``get_db`` will
handle the rest).

Bug injection points:
    * ``calculate_gst`` — may miscalculate GST when WRONG_GST is
      active.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.bugs.injectors import calculate_gst
from app.core.enums import AuditAction, OrderStatus
from app.exceptions.base import (
    BusinessValidationError,
    EntityNotFoundError,
    InvalidOrderError,
    InvalidStateTransitionError,
)
from app.models import Order, OrderItem
from app.repositories.customer import CustomerRepository
from app.repositories.order import OrderRepository
from app.repositories.product import ProductRepository
from app.schemas.order import OrderCreate
from app.services.audit import AuditService
from app.services.coupon import CouponService
from app.services.inventory import InventoryService
from app.utils.helpers import model_to_dict


class OrderService:
    """Service for order lifecycle operations.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = OrderRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_service = InventoryService(db)
        self.coupon_service = CouponService(db)
        self.customer_repo = CustomerRepository(db)
        self.audit_service = AuditService(db)
        self.db = db

    def create_order(
        self,
        data: OrderCreate,
        performed_by: str | None = None,
    ) -> Order:
        """Create a new order with full business workflow.

        Workflow:
            1. Validate customer exists.
            2. Validate all products exist and are active.
            3. Reserve stock for each item via ``InventoryService``.
            4. Calculate subtotal (sum of ``unit_price × quantity``).
            5. Calculate GST per item using the product's
               ``gst_percentage`` via ``calculate_gst()``.
            6. If ``coupon_code`` is provided, validate and compute
               the discount via ``CouponService``.
            7. Compute ``total = subtotal + tax − discount``.
            8. Persist the ``Order`` and its ``OrderItem`` rows.
            9. If the coupon is single-use, mark it as used.
            10. Write an audit log entry.

        On failure after reservations have been made, reserved stock
        is explicitly released before the exception re-raises.

        Args:
            data: Validated order creation payload (with items).
            performed_by: Username of the actor.

        Returns:
            The newly created ``Order`` instance with items loaded.

        Raises:
            EntityNotFoundError: If customer or product does not exist.
            InvalidOrderError: If a product is inactive.
            InsufficientStockError: If stock cannot be reserved.
            InvalidCouponError: If the coupon fails validation.
        """
        # 1. Validate customer exists.
        customer = self.customer_repo.get_by_id(data.customer_id)
        if not customer:
            raise EntityNotFoundError("Customer", data.customer_id)

        # 2. Validate products — collect product objects keyed by ID.
        products: dict[int, object] = {}
        for item in data.items:
            product = self.product_repo.get_by_id(item.product_id)
            if not product:
                raise EntityNotFoundError("Product", item.product_id)
            if not product.active:
                raise InvalidOrderError(
                    message=f"Product '{product.sku}' is inactive and cannot be ordered",
                    details={"product_id": item.product_id, "sku": product.sku},
                )
            products[item.product_id] = product

        # 3. Reserve stock — track what we've reserved for rollback.
        reserved_items: list[tuple[int, int]] = []  # (product_id, quantity)
        try:
            for item in data.items:
                self.inventory_service.reserve_stock(
                    product_id=item.product_id, quantity=item.quantity
                )
                reserved_items.append((item.product_id, item.quantity))

            # 4. Calculate subtotal.
            subtotal = Decimal("0.00")
            order_items_data: list[dict] = []

            for item in data.items:
                product = products[item.product_id]
                unit_price = product.price
                total_price = unit_price * item.quantity
                subtotal += total_price
                order_items_data.append(
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "unit_price": unit_price,
                        "total_price": total_price,
                    }
                )

            # 5. Calculate GST per item and sum.
            tax = Decimal("0.00")
            for item in data.items:
                product = products[item.product_id]
                item_total = product.price * item.quantity
                item_tax = calculate_gst(item_total, product.gst_percentage)
                tax += item_tax

            # 6. Apply coupon discount if provided.
            discount = Decimal("0.00")
            if data.coupon_code:
                discount = self.coupon_service.validate_and_apply(
                    coupon_code=data.coupon_code,
                    order_subtotal=subtotal,
                )

            # 7. Calculate total.
            total = subtotal + tax - discount

            # 8. Create Order and OrderItems.
            order = Order(
                customer_id=data.customer_id,
                status=OrderStatus.PENDING,
                subtotal=subtotal,
                tax=tax,
                discount=discount,
                total=total,
                coupon_code=data.coupon_code,
            )
            created_order = self.repo.create(order)

            for oi_data in order_items_data:
                order_item = OrderItem(
                    order_id=created_order.id,
                    product_id=oi_data["product_id"],
                    quantity=oi_data["quantity"],
                    unit_price=oi_data["unit_price"],
                    total_price=oi_data["total_price"],
                )
                self.db.add(order_item)

            self.db.flush()

            # 9. Mark single-use coupon as used.
            if data.coupon_code:
                coupon = self.coupon_service.repo.get_by_code(data.coupon_code)
                if coupon and coupon.single_use:
                    self.coupon_service.repo.update(coupon, {"used": True})

                    self.audit_service.log(
                        entity="Coupon",
                        entity_id=coupon.id,
                        action=AuditAction.COUPON_APPLIED,
                        new_value={"order_id": created_order.id, "code": data.coupon_code},
                        performed_by=performed_by,
                    )

            # Refresh to load relationships.
            self.db.refresh(created_order)

            logger.info(
                "Order created: id={id} customer={customer_id} total={total}",
                id=created_order.id,
                customer_id=data.customer_id,
                total=total,
            )

            # 10. Audit log.
            self.audit_service.log(
                entity="Order",
                entity_id=created_order.id,
                action=AuditAction.CREATED,
                new_value=created_order,
                performed_by=performed_by,
            )

            return created_order

        except Exception:
            # Release any stock reserved before the failure.
            for product_id, qty in reserved_items:
                try:
                    self.inventory_service.release_stock(product_id, qty)
                except Exception as release_err:
                    logger.error(
                        "Failed to release stock during order rollback: "
                        "product={product_id} qty={qty} error={error}",
                        product_id=product_id,
                        qty=qty,
                        error=str(release_err),
                    )
            raise

    def get_by_id(self, id: int) -> Order:
        """Retrieve an order by primary key with items eagerly loaded.

        Args:
            id: The order's primary key.

        Returns:
            The ``Order`` instance with loaded items and customer.

        Raises:
            EntityNotFoundError: If the order does not exist.
        """
        order = self.repo.get_by_id_with_items(id)
        if not order:
            raise EntityNotFoundError("Order", id)
        return order

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: OrderStatus | None = None,
        customer_id: int | None = None,
    ) -> tuple[list[Order], int]:
        """Retrieve a paginated list of orders.

        Supports optional filtering by status or customer.

        Args:
            page: 1-based page number.
            page_size: Records per page.
            status: Optional status filter.
            customer_id: Optional customer filter.

        Returns:
            A tuple of ``(items, total_count)``.
        """
        skip = (page - 1) * page_size

        if status is not None:
            items = self.repo.get_by_status(status, skip=skip, limit=page_size)
            total = self.repo.count_by_status(status)
        elif customer_id is not None:
            items = self.repo.get_by_customer(
                customer_id, skip=skip, limit=page_size
            )
            # Count is not directly available — use full-list length.
            total = len(
                self.repo.get_by_customer(customer_id, skip=0, limit=999999)
            )
        else:
            items = self.repo.get_all_with_items(skip=skip, limit=page_size)
            total = self.repo.count()

        return items, total

    def update_status(
        self,
        id: int,
        new_status: OrderStatus,
        performed_by: str | None = None,
    ) -> Order:
        """Update the status of an order with state-machine validation.

        Uses ``OrderStatus.can_transition_to`` to enforce allowed
        transitions.  When transitioning to ``CANCELLED``, reserved
        stock for every line item is released.

        Args:
            id: The order's primary key.
            new_status: The target ``OrderStatus``.
            performed_by: Username of the actor.

        Returns:
            The updated ``Order`` instance.

        Raises:
            EntityNotFoundError: If the order does not exist.
            InvalidStateTransitionError: If the transition is not
                allowed by the state machine.
        """
        order = self.get_by_id(id)
        old_status = order.status

        if not old_status.can_transition_to(new_status):
            raise InvalidStateTransitionError(
                entity="Order",
                current_status=old_status.value,
                target_status=new_status.value,
            )

        old_values = model_to_dict(order)

        # Release stock on cancellation.
        if new_status == OrderStatus.CANCELLED:
            for item in order.items:
                self.inventory_service.release_stock(
                    product_id=item.product_id, quantity=item.quantity
                )

        self.repo.update(order, {"status": new_status})

        logger.info(
            "Order status updated: id={id} {old} → {new}",
            id=id,
            old=old_status.value,
            new=new_status.value,
        )

        self.audit_service.log(
            entity="Order",
            entity_id=id,
            action=AuditAction.STATUS_CHANGED,
            old_value=old_values,
            new_value=order,
            performed_by=performed_by,
        )

        return order

    def cancel_order(
        self,
        id: int,
        performed_by: str | None = None,
    ) -> Order:
        """Cancel an order.

        Delegates to ``update_status`` with ``OrderStatus.CANCELLED``.

        Args:
            id: The order's primary key.
            performed_by: Username of the actor.

        Returns:
            The cancelled ``Order`` instance.
        """
        return self.update_status(
            id=id,
            new_status=OrderStatus.CANCELLED,
            performed_by=performed_by,
        )
