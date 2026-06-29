"""Pydantic schema re-exports.

Import all schemas here so ``from app.schemas import ...`` works
for convenience throughout the application.
"""

from app.schemas.audit_log import AuditLogQuery, AuditLogResponse
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenPayload,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from app.schemas.coupon import CouponCreate, CouponResponse, CouponUpdate
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.inventory import InventoryCreate, InventoryResponse, InventoryUpdate
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusUpdate,
)
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
)
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.schemas.report import (
    CustomerReport,
    DateRangeParams,
    InventoryReport,
    OrderReport,
    SalesReport,
)
from app.schemas.shipment import ShipmentCreate, ShipmentResponse, ShipmentStatusUpdate

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",
    # Auth
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "TokenPayload",
    "RefreshTokenRequest",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    # Product
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    # Inventory
    "InventoryCreate",
    "InventoryUpdate",
    "InventoryResponse",
    # Order
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderCreate",
    "OrderStatusUpdate",
    "OrderResponse",
    # Payment
    "PaymentCreate",
    "PaymentResponse",
    "RefundRequest",
    "RefundResponse",
    # Shipment
    "ShipmentCreate",
    "ShipmentStatusUpdate",
    "ShipmentResponse",
    # Coupon
    "CouponCreate",
    "CouponUpdate",
    "CouponResponse",
    # Audit
    "AuditLogResponse",
    "AuditLogQuery",
    # Reports
    "DateRangeParams",
    "SalesReport",
    "OrderReport",
    "InventoryReport",
    "CustomerReport",
]
