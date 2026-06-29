"""Product catalogue management API routes.

Provides CRUD endpoints for products with role-based access control
and optional filtering by active status.
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
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Add a new product to the catalogue. Requires Admin or Manager role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        409: {"model": ErrorResponse, "description": "SKU already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ProductResponse:
    """Create a new product in the catalogue.

    Args:
        data: Product creation payload.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The newly created product.
    """
    service = ProductService(db)
    product = service.create(data, performed_by=current_user.username)
    return ProductResponse.model_validate(product)


@router.get(
    "/",
    response_model=PaginatedResponse[ProductResponse],
    summary="List all products",
    description=(
        "Retrieve a paginated list of products. Optionally filter to show "
        "only active products. Accessible to all authenticated users."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def list_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(False, description="Return only active products"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[ProductResponse]:
    """Retrieve a paginated list of products.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        active_only: If True, only return active products.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Paginated list of products.
    """
    service = ProductService(db)
    items, total = service.get_all(page=page, page_size=page_size, active_only=active_only)
    product_items = [ProductResponse.model_validate(p) for p in items]
    return PaginatedResponse.create(
        items=product_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
    description="Retrieve a single product by its ID. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Product not found"},
    },
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ProductResponse:
    """Retrieve a product by ID.

    Args:
        product_id: The product's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The requested product.
    """
    service = ProductService(db)
    product = service.get_by_id(product_id)
    return ProductResponse.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    description="Update an existing product's details. Requires Admin or Manager role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Product not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ProductResponse:
    """Update an existing product.

    Args:
        product_id: The product's primary key.
        data: Fields to update.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The updated product.
    """
    service = ProductService(db)
    product = service.update(product_id, data, performed_by=current_user.username)
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    response_model=SuccessResponse,
    summary="Soft-delete a product",
    description=(
        "Soft-delete a product by marking it as inactive. "
        "Requires Admin role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Product not found"},
    },
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse:
    """Soft-delete a product (sets active=False).

    Args:
        product_id: The product's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Success confirmation message.
    """
    service = ProductService(db)
    service.delete(product_id, performed_by=current_user.username)
    return SuccessResponse(message=f"Product {product_id} deleted successfully")
