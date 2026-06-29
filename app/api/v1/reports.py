"""Reporting and analytics API routes.

Provides read-only endpoints for sales, orders, inventory, and
customer analytics. All reports require Admin or Manager role.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.auth.permissions import RoleChecker
from app.core.enums import UserRole
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.report import (
    CustomerReport,
    InventoryReport,
    OrderReport,
    SalesReport,
)
from app.services.report import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/sales",
    response_model=SalesReport,
    summary="Sales report",
    description=(
        "Generate an aggregated sales report with total revenue, order count, "
        "average order value, and top-selling products. Optionally filter "
        "by date range. Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
def sales_report(
    start_date: date | None = Query(None, description="Report start date (inclusive)"),
    end_date: date | None = Query(None, description="Report end date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SalesReport:
    """Generate a sales analytics report.

    Args:
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Aggregated sales metrics.
    """
    service = ReportService(db)
    report = service.sales_report(start_date=start_date, end_date=end_date)
    return SalesReport.model_validate(report)


@router.get(
    "/orders",
    response_model=OrderReport,
    summary="Orders report",
    description=(
        "Generate an aggregated orders report with total count, status "
        "breakdown, and recent orders. Optionally filter by date range. "
        "Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
def orders_report(
    start_date: date | None = Query(None, description="Report start date (inclusive)"),
    end_date: date | None = Query(None, description="Report end date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderReport:
    """Generate an orders analytics report.

    Args:
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Aggregated order metrics.
    """
    service = ReportService(db)
    report = service.orders_report(start_date=start_date, end_date=end_date)
    return OrderReport.model_validate(report)


@router.get(
    "/inventory",
    response_model=InventoryReport,
    summary="Inventory report",
    description=(
        "Generate an inventory report with total products, low-stock items, "
        "out-of-stock count, and per-warehouse summaries. "
        "Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
def inventory_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> InventoryReport:
    """Generate an inventory analytics report.

    Args:
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Aggregated inventory metrics.
    """
    service = ReportService(db)
    report = service.inventory_report()
    return InventoryReport.model_validate(report)


@router.get(
    "/customers",
    response_model=CustomerReport,
    summary="Customers report",
    description=(
        "Generate a customer analytics report with total count, top "
        "spenders, and recently registered customers. Optionally filter "
        "by date range. Requires Admin or Manager role."
    ),
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
def customers_report(
    start_date: date | None = Query(None, description="Report start date (inclusive)"),
    end_date: date | None = Query(None, description="Report end date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CustomerReport:
    """Generate a customer analytics report.

    Args:
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Aggregated customer metrics.
    """
    service = ReportService(db)
    report = service.customers_report(start_date=start_date, end_date=end_date)
    return CustomerReport.model_validate(report)
