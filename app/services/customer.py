"""Customer management service.

Provides CRUD operations for customers with business rule
enforcement:

* Duplicate email and phone detection on both create and update.
* Prevention of deleting a customer who has active (non-terminal)
  orders.
* Full audit trail for every mutation.
"""

from loguru import logger
from sqlalchemy.orm import Session

from app.core.enums import AuditAction, OrderStatus
from app.exceptions.base import (
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
)
from app.models import Customer
from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.audit import AuditService
from app.utils.helpers import model_to_dict


class CustomerService:
    """Service for customer lifecycle operations.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = CustomerRepository(db)
        self.audit_service = AuditService(db)
        self.db = db

    def create(
        self,
        data: CustomerCreate,
        performed_by: str | None = None,
    ) -> Customer:
        """Create a new customer.

        Validates that neither the email nor phone number is already
        registered, creates the customer record, and writes an audit
        log entry.

        Args:
            data: Validated customer creation payload.
            performed_by: Username of the actor, if known.

        Returns:
            The newly created ``Customer`` instance.

        Raises:
            ConflictError: If the email or phone is already in use.
        """
        if self.repo.get_by_email(data.email):
            raise ConflictError(
                message=f"Customer with email '{data.email}' already exists",
                details={"field": "email", "value": data.email},
            )

        if self.repo.get_by_phone(data.phone):
            raise ConflictError(
                message=f"Customer with phone '{data.phone}' already exists",
                details={"field": "phone", "value": data.phone},
            )

        customer = Customer(
            name=data.name,
            email=data.email,
            phone=data.phone,
            address=data.address,
            loyalty_points=data.loyalty_points,
        )
        created = self.repo.create(customer)

        logger.info(
            "Customer created: id={id} name={name}",
            id=created.id,
            name=created.name,
        )

        self.audit_service.log(
            entity="Customer",
            entity_id=created.id,
            action=AuditAction.CREATED,
            new_value=created,
            performed_by=performed_by,
        )

        return created

    def get_by_id(self, id: int) -> Customer:
        """Retrieve a customer by primary key.

        Args:
            id: The customer's primary key.

        Returns:
            The ``Customer`` instance.

        Raises:
            EntityNotFoundError: If no customer exists with the given ID.
        """
        customer = self.repo.get_by_id(id)
        if not customer:
            raise EntityNotFoundError("Customer", id)
        return customer

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Customer], int]:
        """Retrieve a paginated list of customers with total count.

        Args:
            page: 1-based page number.
            page_size: Number of records per page.

        Returns:
            A tuple of ``(items, total_count)``.
        """
        skip = (page - 1) * page_size
        items = self.repo.get_all(skip=skip, limit=page_size)
        total = self.repo.count()
        return items, total

    def update(
        self,
        id: int,
        data: CustomerUpdate,
        performed_by: str | None = None,
    ) -> Customer:
        """Update an existing customer.

        Only fields present in *data* (non-``None``) are applied.
        Uniqueness constraints on email and phone are re-validated
        when those fields change.

        Args:
            id: The customer's primary key.
            data: Validated partial-update payload.
            performed_by: Username of the actor.

        Returns:
            The updated ``Customer`` instance.

        Raises:
            EntityNotFoundError: If the customer does not exist.
            ConflictError: If the new email or phone collides with
                another customer.
        """
        customer = self.get_by_id(id)
        old_values = model_to_dict(customer)

        update_data = data.model_dump(exclude_unset=True)

        # Validate email uniqueness when changing.
        if "email" in update_data and update_data["email"] != customer.email:
            existing = self.repo.get_by_email(update_data["email"])
            if existing and existing.id != id:
                raise ConflictError(
                    message=f"Customer with email '{update_data['email']}' already exists",
                    details={"field": "email", "value": update_data["email"]},
                )

        # Validate phone uniqueness when changing.
        if "phone" in update_data and update_data["phone"] != customer.phone:
            existing = self.repo.get_by_phone(update_data["phone"])
            if existing and existing.id != id:
                raise ConflictError(
                    message=f"Customer with phone '{update_data['phone']}' already exists",
                    details={"field": "phone", "value": update_data["phone"]},
                )

        updated = self.repo.update(customer, update_data)

        logger.info("Customer updated: id={id}", id=id)

        self.audit_service.log(
            entity="Customer",
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
        """Delete a customer.

        Prevents deletion when the customer has orders in non-terminal
        statuses (i.e. anything other than ``DELIVERED`` or
        ``CANCELLED``).

        Args:
            id: The customer's primary key.
            performed_by: Username of the actor.

        Raises:
            EntityNotFoundError: If the customer does not exist.
            BusinessValidationError: If the customer has active orders.
        """
        customer = self.get_by_id(id)

        # Guard: no deletion if active (non-terminal) orders exist.
        active_orders = [
            order
            for order in customer.orders
            if not order.status.is_terminal
        ]
        if active_orders:
            raise BusinessValidationError(
                message=f"Cannot delete customer with {len(active_orders)} active order(s)",
                details={
                    "customer_id": id,
                    "active_order_ids": [o.id for o in active_orders],
                },
            )

        old_values = model_to_dict(customer)
        self.repo.delete(customer)

        logger.info("Customer deleted: id={id}", id=id)

        self.audit_service.log(
            entity="Customer",
            entity_id=id,
            action=AuditAction.DELETED,
            old_value=old_values,
            performed_by=performed_by,
        )
