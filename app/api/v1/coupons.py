"""Coupon management API routes.

Provides endpoints for creating, listing, retrieving, updating,
and deactivating discount coupons. Coupons are identified by their
unique code rather than numeric ID.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.auth.permissions import RoleChecker
from app.core.enums import UserRole
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from app.schemas.coupon import CouponCreate, CouponResponse, CouponUpdate
from app.services.coupon import CouponService

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.post(
    "/",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new coupon",
    description="Create a new discount coupon. Requires Admin role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        409: {"model": ErrorResponse, "description": "Coupon code already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CouponResponse:
    """Create a new coupon.

    Args:
        data: Coupon creation payload.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The newly created coupon.
    """
    service = CouponService(db)
    coupon = service.create(data, performed_by=current_user.username)
    return CouponResponse.model_validate(coupon)


@router.get(
    "/",
    response_model=PaginatedResponse[CouponResponse],
    summary="List all coupons",
    description="Retrieve a paginated list of all coupons. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def list_coupons(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[CouponResponse]:
    """Retrieve a paginated list of coupons.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Paginated list of coupons.
    """
    service = CouponService(db)
    items, total = service.get_all(page=page, page_size=page_size)
    coupon_items = [CouponResponse.model_validate(c) for c in items]
    return PaginatedResponse.create(
        items=coupon_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{code}",
    response_model=CouponResponse,
    summary="Get coupon by code",
    description="Retrieve a single coupon by its unique code. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Coupon not found"},
    },
)
def get_coupon(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CouponResponse:
    """Retrieve a coupon by code.

    Args:
        code: The coupon's unique code.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The requested coupon.
    """
    service = CouponService(db)
    coupon = service.get_by_code(code)
    return CouponResponse.model_validate(coupon)


@router.put(
    "/{code}",
    response_model=CouponResponse,
    summary="Update a coupon",
    description="Update an existing coupon's details. Requires Admin role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Coupon not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def update_coupon(
    code: str,
    data: CouponUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CouponResponse:
    """Update an existing coupon.

    Args:
        code: The coupon's unique code.
        data: Fields to update.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The updated coupon.
    """
    service = CouponService(db)
    coupon = service.update(code, data, performed_by=current_user.username)
    return CouponResponse.model_validate(coupon)


@router.delete(
    "/{code}",
    response_model=SuccessResponse,
    summary="Deactivate a coupon",
    description="Deactivate a coupon by its code. Requires Admin role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Coupon not found"},
    },
)
def deactivate_coupon(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse:
    """Deactivate a coupon.

    Args:
        code: The coupon's unique code.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Success confirmation message.
    """
    service = CouponService(db)
    service.deactivate(code, performed_by=current_user.username)
    return SuccessResponse(message=f"Coupon '{code}' deactivated successfully")
