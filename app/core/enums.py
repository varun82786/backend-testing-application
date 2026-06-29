"""Enumeration types for the OMS domain.

Centralizes all status enums and type constants used across the application.
Using Python's Enum ensures type safety and self-documenting code.
"""

from enum import Enum


class OrderStatus(str, Enum):
    """Order lifecycle statuses.

    Allowed transitions:
        Pending  → Paid, Cancelled
        Paid     → Packed, Cancelled
        Packed   → Shipped, Cancelled
        Shipped  → Delivered
        Delivered → (terminal)
        Cancelled → (terminal)
    """

    PENDING = "pending"
    PAID = "paid"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    @classmethod
    def allowed_transitions(cls) -> dict["OrderStatus", list["OrderStatus"]]:
        """Return the mapping of allowed status transitions."""
        return {
            cls.PENDING: [cls.PAID, cls.CANCELLED],
            cls.PAID: [cls.PACKED, cls.CANCELLED],
            cls.PACKED: [cls.SHIPPED, cls.CANCELLED],
            cls.SHIPPED: [cls.DELIVERED],
            cls.DELIVERED: [],
            cls.CANCELLED: [],
        }

    def can_transition_to(self, target: "OrderStatus") -> bool:
        """Check if transition from current status to target is allowed."""
        return target in self.allowed_transitions().get(self, [])

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal (final) status."""
        return self in (self.DELIVERED, self.CANCELLED)


class PaymentStatus(str, Enum):
    """Payment processing statuses.

    Allowed transitions:
        Pending  → Success, Failed
        Success  → Refunded
        Failed   → (terminal)
        Refunded → (terminal)
    """

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

    @classmethod
    def allowed_transitions(cls) -> dict["PaymentStatus", list["PaymentStatus"]]:
        """Return the mapping of allowed status transitions."""
        return {
            cls.PENDING: [cls.SUCCESS, cls.FAILED],
            cls.SUCCESS: [cls.REFUNDED],
            cls.FAILED: [],
            cls.REFUNDED: [],
        }

    def can_transition_to(self, target: "PaymentStatus") -> bool:
        """Check if transition from current status to target is allowed."""
        return target in self.allowed_transitions().get(self, [])


class ShipmentStatus(str, Enum):
    """Shipment tracking statuses.

    Allowed transitions:
        Pending → Packed
        Packed  → Shipped
        Shipped → Delivered
    """

    PENDING = "pending"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

    @classmethod
    def allowed_transitions(cls) -> dict["ShipmentStatus", list["ShipmentStatus"]]:
        """Return the mapping of allowed status transitions."""
        return {
            cls.PENDING: [cls.PACKED],
            cls.PACKED: [cls.SHIPPED],
            cls.SHIPPED: [cls.DELIVERED],
            cls.DELIVERED: [],
        }

    def can_transition_to(self, target: "ShipmentStatus") -> bool:
        """Check if transition from current status to target is allowed."""
        return target in self.allowed_transitions().get(self, [])


class PaymentMethod(str, Enum):
    """Supported payment methods."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    CASH_ON_DELIVERY = "cash_on_delivery"


class DiscountType(str, Enum):
    """Coupon discount types."""

    PERCENTAGE = "percentage"
    FLAT = "flat"


class UserRole(str, Enum):
    """User authorization roles.

    Role hierarchy:
        Admin   → Full access to all resources and operations.
        Manager → CRUD on business entities, reports, no user management.
        User    → Read access + create orders + process payments.
    """

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class AuditAction(str, Enum):
    """Audit log action types."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    PAYMENT_PROCESSED = "payment_processed"
    PAYMENT_REFUNDED = "payment_refunded"
    STOCK_RESERVED = "stock_reserved"
    STOCK_RELEASED = "stock_released"
    STOCK_DEDUCTED = "stock_deducted"
    COUPON_APPLIED = "coupon_applied"
    LOGIN = "login"
    REGISTER = "register"
