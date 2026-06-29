"""Repository for Coupon entity data access."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Coupon
from app.repositories.base import BaseRepository


class CouponRepository(BaseRepository[Coupon]):
    """Repository for ``Coupon`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with coupon-specific queries such as
    code lookup and active (non-expired, usage-remaining) filtering.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the CouponRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(Coupon, db)

    def get_by_code(self, code: str) -> Coupon | None:
        """Retrieve a coupon by its unique code.

        The lookup is case-sensitive.

        Args:
            code: The coupon code string.

        Returns:
            The matching ``Coupon`` instance, or ``None`` if not found.
        """
        stmt = select(Coupon).where(Coupon.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active(self, skip: int = 0, limit: int = 20) -> list[Coupon]:
        """Retrieve a paginated list of currently active coupons.

        A coupon is considered active when:
        - ``is_active`` is ``True``
        - ``valid_from`` is at or before the current UTC time
        - ``valid_until`` is after the current UTC time

        Args:
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 20.

        Returns:
            A list of active ``Coupon`` instances.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Coupon)
            .where(
                Coupon.is_active.is_(True),
                Coupon.valid_from <= now,
                Coupon.valid_until > now,
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
