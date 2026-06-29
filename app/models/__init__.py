"""ORM model re-exports.

Import all models here so that ``from app.models import ...`` works
and so that Alembic can discover every table via ``Base.metadata``.
"""

from app.models.audit_log import AuditLog
from app.models.coupon import Coupon
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.user import User

__all__ = [
    "User",
    "Customer",
    "Product",
    "Inventory",
    "Order",
    "OrderItem",
    "Payment",
    "Shipment",
    "Coupon",
    "AuditLog",
]
