"""Customer management API routes.

Provides CRUD endpoints for customer records with role-based
access control.
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
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customer import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
    description="Create a new customer record. Requires Admin or Manager role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        409: {"model": ErrorResponse, "description": "Customer email already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CustomerResponse:
    """Create a new customer.

    Args:
        data: Customer creation payload.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The newly created customer.
    """
    service = CustomerService(db)
    customer = service.create(data, performed_by=current_user.username)
    return CustomerResponse.model_validate(customer)


@router.get(
    "/",
    response_model=PaginatedResponse[CustomerResponse],
    summary="List all customers",
    description="Retrieve a paginated list of customers. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def list_customers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[CustomerResponse]:
    """Retrieve a paginated list of all customers.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Paginated list of customers.
    """
    service = CustomerService(db)
    items, total = service.get_all(page=page, page_size=page_size)
    customer_items = [CustomerResponse.model_validate(c) for c in items]
    return PaginatedResponse.create(
        items=customer_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer by ID",
    description="Retrieve a single customer by their ID. Accessible to all authenticated users.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Customer not found"},
    },
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CustomerResponse:
    """Retrieve a customer by ID.

    Args:
        customer_id: The customer's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The requested customer.
    """
    service = CustomerService(db)
    customer = service.get_by_id(customer_id)
    return CustomerResponse.model_validate(customer)


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update a customer",
    description="Update an existing customer's details. Requires Admin or Manager role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Customer not found"},
        409: {"model": ErrorResponse, "description": "Email conflict"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CustomerResponse:
    """Update an existing customer.

    Args:
        customer_id: The customer's primary key.
        data: Fields to update.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The updated customer.
    """
    service = CustomerService(db)
    customer = service.update(customer_id, data, performed_by=current_user.username)
    return CustomerResponse.model_validate(customer)


@router.delete(
    "/{customer_id}",
    response_model=SuccessResponse,
    summary="Delete a customer",
    description="Delete a customer record. Requires Admin role.",
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Customer not found"},
    },
)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse:
    """Delete a customer by ID.

    Args:
        customer_id: The customer's primary key.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Success confirmation message.
    """
    service = CustomerService(db)
    service.delete(customer_id, performed_by=current_user.username)
    return SuccessResponse(message=f"Customer {customer_id} deleted successfully")
