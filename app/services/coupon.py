"""Coupon management service.

Provides CRUD operations and the ``validate_and_apply`` method used
during order creation to compute the discount for a coupon code.

Validation checks for ``validate_and_apply``:
    * Coupon exists.
    * Coupon is active.
    * Coupon has not expired.
    * Single-use coupons have not already been redeemed.
    * The order subtotal meets the minimum requirement.
"""

from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core.enums import AuditAction, DiscountType
from app.exceptions.base import (
    ConflictError,
    EntityNotFoundError,
    InvalidCouponError,
)
from app.models import Coupon
from app.repositories.coupon import CouponRepository
from app.schemas.coupon import CouponCreate, CouponUpdate
from app.services.audit import AuditService
from app.utils.helpers import model_to_dict


class CouponService:
    """Service for coupon lifecycle and discount calculation.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.repo = CouponRepository(db)
        self.audit_service = AuditService(db)
        self.db = db

    def create(
        self,
        data: CouponCreate,
        performed_by: str | None = None,
    ) -> Coupon:
        """Create a new coupon.

        Validates that the coupon code is not already in use.

        Args:
            data: Validated coupon creation payload.
            performed_by: Username of the actor.

        Returns:
            The newly created ``Coupon`` instance.

        Raises:
            ConflictError: If a coupon with the same code already exists.
        """
        if self.repo.get_by_code(data.code):
            raise ConflictError(
                message=f"Coupon with code '{data.code}' already exists",
                details={"field": "code", "value": data.code},
            )

        coupon = Coupon(
            code=data.code,
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            minimum_order=data.minimum_order,
            expiry=data.expiry,
            active=data.active,
            single_use=data.single_use,
            used=False,
        )
        created = self.repo.create(coupon)

        logger.info(
            "Coupon created: code={code} type={dtype}",
            code=created.code,
            dtype=created.discount_type.value,
        )

        self.audit_service.log(
            entity="Coupon",
            entity_id=created.id,
            action=AuditAction.CREATED,
            new_value=created,
            performed_by=performed_by,
        )

        return created

    def get_by_code(self, code: str) -> Coupon:
        """Retrieve a coupon by its unique code.

        Args:
            code: The coupon code string.

        Returns:
            The ``Coupon`` instance.

        Raises:
            EntityNotFoundError: If no coupon exists with the given code.
        """
        coupon = self.repo.get_by_code(code)
        if not coupon:
            raise EntityNotFoundError("Coupon", code)
        return coupon

    def get_by_id(self, id: int) -> Coupon:
        """Retrieve a coupon by primary key.

        Args:
            id: The coupon's primary key.

        Returns:
            The ``Coupon`` instance.

        Raises:
            EntityNotFoundError: If no coupon exists with the given ID.
        """
        coupon = self.repo.get_by_id(id)
        if not coupon:
            raise EntityNotFoundError("Coupon", id)
        return coupon

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Coupon], int]:
        """Retrieve a paginated list of all coupons.

        Args:
            page: 1-based page number.
            page_size: Records per page.

        Returns:
            A tuple of ``(items, total_count)``.
        """
        skip = (page - 1) * page_size
        items = self.repo.get_all(skip=skip, limit=page_size)
        total = self.repo.count()
        return items, total

    def update(
        self,
        code: str,
        data: CouponUpdate,
        performed_by: str | None = None,
    ) -> Coupon:
        """Update an existing coupon.

        Args:
            code: The coupon's unique code.
            data: Validated partial-update payload.
            performed_by: Username of the actor.

        Returns:
            The updated ``Coupon`` instance.

        Raises:
            EntityNotFoundError: If the coupon does not exist.
        """
        coupon = self.get_by_code(code)
        old_values = model_to_dict(coupon)

        update_data = data.model_dump(exclude_unset=True)
        updated = self.repo.update(coupon, update_data)

        logger.info("Coupon updated: code={code}", code=code)

        self.audit_service.log(
            entity="Coupon",
            entity_id=coupon.id,
            action=AuditAction.UPDATED,
            old_value=old_values,
            new_value=updated,
            performed_by=performed_by,
        )

        return updated

    def deactivate(
        self,
        code: str,
        performed_by: str | None = None,
    ) -> None:
        """Deactivate a coupon so it can no longer be applied.

        Args:
            code: The coupon's unique code.
            performed_by: Username of the actor.

        Raises:
            EntityNotFoundError: If the coupon does not exist.
        """
        coupon = self.get_by_code(code)
        old_values = model_to_dict(coupon)

        self.repo.update(coupon, {"active": False})

        logger.info("Coupon deactivated: code={code}", code=code)

        self.audit_service.log(
            entity="Coupon",
            entity_id=coupon.id,
            action=AuditAction.UPDATED,
            old_value=old_values,
            new_value=coupon,
            performed_by=performed_by,
        )

    def validate_and_apply(
        self,
        coupon_code: str,
        order_subtotal: Decimal,
    ) -> Decimal:
        """Validate a coupon and compute the discount amount.

        Runs the full validation gauntlet (existence, active, not
        expired, not already used if single-use, minimum order met)
        and returns the calculated discount.

        For ``PERCENTAGE`` coupons the discount is capped at the
        order subtotal.  For ``FLAT`` coupons the discount is
        the face value (but also capped at subtotal).

        Args:
            coupon_code: The coupon code to validate.
            order_subtotal: The pre-tax, pre-discount order subtotal.

        Returns:
            The ``Decimal`` discount amount to apply.

        Raises:
            InvalidCouponError: If any validation check fails.
        """
        coupon = self.repo.get_by_code(coupon_code)

        if not coupon:
            raise InvalidCouponError(
                message=f"Coupon '{coupon_code}' not found",
                details={"code": coupon_code},
            )

        if not coupon.active:
            raise InvalidCouponError(
                message=f"Coupon '{coupon_code}' is inactive",
                details={"code": coupon_code},
            )

        now = datetime.now(timezone.utc)
        if coupon.expiry <= now:
            raise InvalidCouponError(
                message=f"Coupon '{coupon_code}' has expired",
                details={"code": coupon_code, "expiry": str(coupon.expiry)},
            )

        if coupon.single_use and coupon.used:
            raise InvalidCouponError(
                message=f"Coupon '{coupon_code}' has already been used",
                details={"code": coupon_code},
            )

        if order_subtotal < coupon.minimum_order:
            raise InvalidCouponError(
                message=(
                    f"Order subtotal {order_subtotal} does not meet minimum "
                    f"order requirement of {coupon.minimum_order}"
                ),
                details={
                    "code": coupon_code,
                    "subtotal": str(order_subtotal),
                    "minimum_order": str(coupon.minimum_order),
                },
            )

        # Calculate discount.
        if coupon.discount_type == DiscountType.PERCENTAGE:
            discount = order_subtotal * coupon.discount_value / Decimal("100")
        else:  # FLAT
            discount = coupon.discount_value

        # Never discount more than the subtotal.
        discount = min(discount, order_subtotal)

        logger.info(
            "Coupon validated: code={code} discount={discount}",
            code=coupon_code,
            discount=discount,
        )

        return discount
