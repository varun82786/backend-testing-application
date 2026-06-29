"""Report Pydantic schemas.

Read-only response schemas for analytics and reporting endpoints.
These are never used as input schemas — they are always computed
by the service layer.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ── Query Parameters ───────────────────────────────────────────────


class DateRangeParams(BaseModel):
    """Date range filter for report endpoints.

    Attributes:
        start_date: Inclusive start date.
        end_date: Inclusive end date (defaults to today).
    """

    start_date: date = Field(description="Report start date (inclusive)")
    end_date: date | None = Field(
        default=None, description="Report end date (inclusive, defaults to today)"
    )


# ── Sales Report ───────────────────────────────────────────────────


class TopProduct(BaseModel):
    """A product entry within the sales report top-sellers list.

    Attributes:
        product_id: Product primary key.
        product_name: Product name.
        total_quantity: Total units sold.
        total_revenue: Total revenue from this product.
    """

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    total_quantity: int
    total_revenue: Decimal


class SalesReport(BaseModel):
    """Aggregated sales metrics for a date range.

    Attributes:
        total_revenue: Sum of all order totals.
        total_orders: Number of orders.
        average_order_value: Mean order total.
        top_products: Best-selling products.
    """

    model_config = ConfigDict(from_attributes=True)

    total_revenue: Decimal = Field(description="Sum of all order totals")
    total_orders: int = Field(description="Number of orders")
    average_order_value: Decimal = Field(description="Mean order total")
    top_products: list[TopProduct] = Field(
        default_factory=list, description="Best-selling products"
    )


# ── Order Report ───────────────────────────────────────────────────


class RecentOrder(BaseModel):
    """Abbreviated order entry for the order report.

    Attributes:
        id: Order primary key.
        customer_id: Customer FK.
        status: Current order status.
        total: Order total.
        created_at: Order creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: str
    total: Decimal
    created_at: datetime


class OrderReport(BaseModel):
    """Aggregated order metrics.

    Attributes:
        total: Total number of orders.
        by_status: Count of orders grouped by status.
        recent_orders: Most recent orders.
    """

    model_config = ConfigDict(from_attributes=True)

    total: int = Field(description="Total order count")
    by_status: dict[str, int] = Field(
        default_factory=dict, description="Orders grouped by status"
    )
    recent_orders: list[RecentOrder] = Field(
        default_factory=list, description="Most recent orders"
    )


# ── Inventory Report ──────────────────────────────────────────────


class WarehouseSummary(BaseModel):
    """Per-warehouse stock summary.

    Attributes:
        warehouse: Warehouse identifier.
        total_quantity: Total on-hand stock.
        total_reserved: Total reserved stock.
        product_count: Number of distinct products.
    """

    model_config = ConfigDict(from_attributes=True)

    warehouse: str
    total_quantity: int
    total_reserved: int
    product_count: int


class LowStockItem(BaseModel):
    """Product with stock below a threshold.

    Attributes:
        product_id: Product primary key.
        product_name: Product name.
        sku: Product SKU.
        warehouse: Warehouse identifier.
        quantity: Current on-hand quantity.
        reserved_quantity: Currently reserved.
    """

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    sku: str
    warehouse: str
    quantity: int
    reserved_quantity: int


class InventoryReport(BaseModel):
    """Aggregated inventory metrics.

    Attributes:
        total_products: Number of distinct products with inventory.
        low_stock_items: Products below the low-stock threshold.
        out_of_stock: Count of products with zero stock.
        warehouse_summary: Per-warehouse rollup.
    """

    model_config = ConfigDict(from_attributes=True)

    total_products: int = Field(description="Distinct products with inventory")
    low_stock_items: list[LowStockItem] = Field(
        default_factory=list, description="Low-stock products"
    )
    out_of_stock: int = Field(description="Products with zero stock")
    warehouse_summary: list[WarehouseSummary] = Field(
        default_factory=list, description="Per-warehouse summary"
    )


# ── Customer Report ───────────────────────────────────────────────


class TopSpender(BaseModel):
    """Customer entry in the top-spenders list.

    Attributes:
        customer_id: Customer primary key.
        customer_name: Customer name.
        total_spent: Cumulative spend.
        order_count: Number of orders placed.
    """

    model_config = ConfigDict(from_attributes=True)

    customer_id: int
    customer_name: str
    total_spent: Decimal
    order_count: int


class RecentCustomer(BaseModel):
    """Abbreviated customer entry for the customer report.

    Attributes:
        id: Customer primary key.
        name: Customer name.
        email: Customer email.
        created_at: Registration timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class CustomerReport(BaseModel):
    """Aggregated customer metrics.

    Attributes:
        total_customers: Total registered customers.
        top_spenders: Highest-spending customers.
        recent_customers: Most recently registered customers.
    """

    model_config = ConfigDict(from_attributes=True)

    total_customers: int = Field(description="Total registered customers")
    top_spenders: list[TopSpender] = Field(
        default_factory=list, description="Highest-spending customers"
    )
    recent_customers: list[RecentCustomer] = Field(
        default_factory=list, description="Recently registered customers"
    )
