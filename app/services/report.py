"""Reporting service.

Provides aggregated analytics queries across orders, inventory, and
customers.  All queries use SQLAlchemy 2.x ``select()`` / ``func``
syntax and are read-only — no mutations or audit logging.

Revenue calculations only include orders in "paid-or-later" statuses:
``PAID``, ``PACKED``, ``SHIPPED``, ``DELIVERED``.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus
from app.models import Customer, Inventory, Order, OrderItem, Product


# Statuses that contribute to revenue / sales counts.
_REVENUE_STATUSES = {
    OrderStatus.PAID,
    OrderStatus.PACKED,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
}


class ReportService:
    """Service for read-only analytics and reporting.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Sales Report ───────────────────────────────────────────────

    def sales_report(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Generate a sales report.

        Returns aggregated revenue, order count, average order value,
        and top 10 products by total quantity ordered.

        Only orders with status in (PAID, PACKED, SHIPPED, DELIVERED)
        are counted.

        Args:
            start_date: Inclusive start date filter on ``Order.created_at``.
            end_date: Inclusive end date filter on ``Order.created_at``.

        Returns:
            A dict with keys ``total_revenue``, ``total_orders``,
            ``average_order_value``, and ``top_products``.
        """
        # Base filter: revenue-eligible statuses.
        filters = [Order.status.in_(_REVENUE_STATUSES)]
        if start_date is not None:
            filters.append(
                Order.created_at >= datetime(
                    start_date.year, start_date.month, start_date.day,
                    tzinfo=timezone.utc,
                )
            )
        if end_date is not None:
            filters.append(
                Order.created_at <= datetime(
                    end_date.year, end_date.month, end_date.day,
                    23, 59, 59,
                    tzinfo=timezone.utc,
                )
            )

        # Aggregates.
        stmt = select(
            func.coalesce(func.sum(Order.total), Decimal("0.00")).label("total_revenue"),
            func.count(Order.id).label("total_orders"),
        ).where(*filters)
        row = self.db.execute(stmt).one()
        total_revenue = Decimal(str(row.total_revenue))
        total_orders = row.total_orders
        average_order_value = (
            total_revenue / total_orders if total_orders > 0 else Decimal("0.00")
        )

        # Top 10 products by quantity.
        top_stmt = (
            select(
                OrderItem.product_id,
                Product.name.label("product_name"),
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.total_price).label("total_revenue"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .where(*filters)
            .group_by(OrderItem.product_id, Product.name)
            .order_by(desc("total_quantity"))
            .limit(10)
        )
        top_products = [
            {
                "product_id": r.product_id,
                "product_name": r.product_name,
                "total_quantity": r.total_quantity,
                "total_revenue": Decimal(str(r.total_revenue)),
            }
            for r in self.db.execute(top_stmt).all()
        ]

        logger.info(
            "Sales report generated: orders={orders} revenue={revenue}",
            orders=total_orders,
            revenue=total_revenue,
        )

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "average_order_value": average_order_value,
            "top_products": top_products,
        }

    # ── Orders Report ──────────────────────────────────────────────

    def orders_report(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Generate an orders summary report.

        Returns total order count, count grouped by status, and the
        10 most recent orders.

        Args:
            start_date: Inclusive start date filter.
            end_date: Inclusive end date filter.

        Returns:
            A dict with keys ``total``, ``by_status``, and
            ``recent_orders``.
        """
        filters: list = []
        if start_date is not None:
            filters.append(
                Order.created_at >= datetime(
                    start_date.year, start_date.month, start_date.day,
                    tzinfo=timezone.utc,
                )
            )
        if end_date is not None:
            filters.append(
                Order.created_at <= datetime(
                    end_date.year, end_date.month, end_date.day,
                    23, 59, 59,
                    tzinfo=timezone.utc,
                )
            )

        # Total count.
        total_stmt = select(func.count(Order.id)).where(*filters) if filters else select(func.count(Order.id))
        total = self.db.execute(total_stmt).scalar_one()

        # Count by status.
        by_status: dict[str, int] = {}
        for status in OrderStatus:
            status_filters = [Order.status == status] + filters
            count_stmt = select(func.count(Order.id)).where(*status_filters)
            count = self.db.execute(count_stmt).scalar_one()
            by_status[status.value] = count

        # 10 most recent orders.
        recent_stmt = (
            select(Order)
            .where(*filters)
            .order_by(desc(Order.created_at))
            .limit(10)
        ) if filters else (
            select(Order)
            .order_by(desc(Order.created_at))
            .limit(10)
        )
        recent_orders = [
            {
                "id": o.id,
                "customer_id": o.customer_id,
                "status": o.status.value,
                "total": o.total,
                "created_at": o.created_at,
            }
            for o in self.db.execute(recent_stmt).scalars().all()
        ]

        logger.info("Orders report generated: total={total}", total=total)

        return {
            "total": total,
            "by_status": by_status,
            "recent_orders": recent_orders,
        }

    # ── Inventory Report ──────────────────────────────────────────

    def inventory_report(self) -> dict:
        """Generate an inventory summary report.

        Returns total distinct products with inventory, items with
        quantity below 10 (low stock), count of out-of-stock items,
        and per-warehouse rollup.

        Returns:
            A dict with keys ``total_products``, ``low_stock_items``,
            ``out_of_stock``, and ``warehouse_summary``.
        """
        # Total distinct products.
        total_stmt = select(
            func.count(func.distinct(Inventory.product_id))
        )
        total_products = self.db.execute(total_stmt).scalar_one()

        # Low stock (quantity < 10).
        low_stmt = (
            select(Inventory)
            .join(Product, Product.id == Inventory.product_id)
            .where(Inventory.quantity < 10)
        )
        low_stock_items = [
            {
                "product_id": inv.product_id,
                "product_name": inv.product.name if inv.product else "Unknown",
                "sku": inv.product.sku if inv.product else "Unknown",
                "warehouse": inv.warehouse,
                "quantity": inv.quantity,
                "reserved_quantity": inv.reserved_quantity,
            }
            for inv in self.db.execute(low_stmt).scalars().all()
        ]

        # Out of stock count.
        oos_stmt = select(func.count(Inventory.id)).where(Inventory.quantity == 0)
        out_of_stock = self.db.execute(oos_stmt).scalar_one()

        # Per-warehouse summary.
        wh_stmt = (
            select(
                Inventory.warehouse,
                func.sum(Inventory.quantity).label("total_quantity"),
                func.sum(Inventory.reserved_quantity).label("total_reserved"),
                func.count(Inventory.id).label("product_count"),
            )
            .group_by(Inventory.warehouse)
        )
        warehouse_summary = [
            {
                "warehouse": r.warehouse,
                "total_quantity": r.total_quantity or 0,
                "total_reserved": r.total_reserved or 0,
                "product_count": r.product_count,
            }
            for r in self.db.execute(wh_stmt).all()
        ]

        logger.info(
            "Inventory report generated: products={total} low_stock={low}",
            total=total_products,
            low=len(low_stock_items),
        )

        return {
            "total_products": total_products,
            "low_stock_items": low_stock_items,
            "out_of_stock": out_of_stock,
            "warehouse_summary": warehouse_summary,
        }

    # ── Customers Report ──────────────────────────────────────────

    def customers_report(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Generate a customer analytics report.

        Returns total customer count, top 10 spenders (by cumulative
        order total), and 10 most recently created customers.

        Args:
            start_date: Inclusive start date filter on ``Customer.created_at``.
            end_date: Inclusive end date filter on ``Customer.created_at``.

        Returns:
            A dict with keys ``total_customers``, ``top_spenders``,
            and ``recent_customers``.
        """
        customer_filters: list = []
        if start_date is not None:
            customer_filters.append(
                Customer.created_at >= datetime(
                    start_date.year, start_date.month, start_date.day,
                    tzinfo=timezone.utc,
                )
            )
        if end_date is not None:
            customer_filters.append(
                Customer.created_at <= datetime(
                    end_date.year, end_date.month, end_date.day,
                    23, 59, 59,
                    tzinfo=timezone.utc,
                )
            )

        # Total customers.
        total_stmt = (
            select(func.count(Customer.id)).where(*customer_filters)
            if customer_filters
            else select(func.count(Customer.id))
        )
        total_customers = self.db.execute(total_stmt).scalar_one()

        # Top 10 spenders (by sum of order totals, revenue-eligible).
        spender_stmt = (
            select(
                Customer.id.label("customer_id"),
                Customer.name.label("customer_name"),
                func.coalesce(func.sum(Order.total), Decimal("0.00")).label("total_spent"),
                func.count(Order.id).label("order_count"),
            )
            .join(Order, Order.customer_id == Customer.id)
            .where(Order.status.in_(_REVENUE_STATUSES))
            .group_by(Customer.id, Customer.name)
            .order_by(desc("total_spent"))
            .limit(10)
        )
        top_spenders = [
            {
                "customer_id": r.customer_id,
                "customer_name": r.customer_name,
                "total_spent": Decimal(str(r.total_spent)),
                "order_count": r.order_count,
            }
            for r in self.db.execute(spender_stmt).all()
        ]

        # 10 most recently created customers.
        recent_stmt = (
            select(Customer)
            .where(*customer_filters)
            .order_by(desc(Customer.created_at))
            .limit(10)
        ) if customer_filters else (
            select(Customer)
            .order_by(desc(Customer.created_at))
            .limit(10)
        )
        recent_customers = [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "created_at": c.created_at,
            }
            for c in self.db.execute(recent_stmt).scalars().all()
        ]

        logger.info(
            "Customers report generated: total={total}",
            total=total_customers,
        )

        return {
            "total_customers": total_customers,
            "top_spenders": top_spenders,
            "recent_customers": recent_customers,
        }
