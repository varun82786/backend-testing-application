"""Repository layer for data access.

Provides the data access layer following the Repository pattern.
All repositories inherit from ``BaseRepository`` and use SQLAlchemy 2.x
``select()`` syntax.  Repositories never commit — the service layer
manages transactions.
"""

from app.repositories.audit_log import AuditLogRepository
from app.repositories.base import BaseRepository
from app.repositories.coupon import CouponRepository
from app.repositories.customer import CustomerRepository
from app.repositories.inventory import InventoryRepository
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.repositories.product import ProductRepository
from app.repositories.shipment import ShipmentRepository
from app.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "AuditLogRepository",
    "CouponRepository",
    "CustomerRepository",
    "InventoryRepository",
    "OrderRepository",
    "PaymentRepository",
    "ProductRepository",
    "ShipmentRepository",
    "UserRepository",
]
