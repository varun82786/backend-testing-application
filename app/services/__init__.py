"""Service layer for business logic.

Provides the service layer following clean architecture principles.
Services orchestrate repositories, enforce business rules, and
manage audit logging.  Services never raise ``HTTPException`` —
they use domain exceptions from ``app.exceptions.base``.
"""

from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.coupon import CouponService
from app.services.customer import CustomerService
from app.services.inventory import InventoryService
from app.services.order import OrderService
from app.services.payment import PaymentService
from app.services.report import ReportService
from app.services.shipment import ShipmentService

__all__ = [
    "AuditService",
    "AuthService",
    "CouponService",
    "CustomerService",
    "InventoryService",
    "OrderService",
    "PaymentService",
    "ReportService",
    "ShipmentService",
]
