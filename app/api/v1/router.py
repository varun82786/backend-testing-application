"""Aggregated API v1 router.

Includes all v1 sub-routers under the ``/api/v1`` prefix.
Import this single router in ``main.py`` to mount the entire API.
"""

from fastapi import APIRouter

from app.api.v1 import (
    audit_logs,
    auth,
    coupons,
    customers,
    inventory,
    orders,
    payments,
    products,
    reports,
    shipments,
)

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(customers.router)
api_v1_router.include_router(products.router)
api_v1_router.include_router(inventory.router)
api_v1_router.include_router(orders.router)
api_v1_router.include_router(payments.router)
api_v1_router.include_router(shipments.router)
api_v1_router.include_router(coupons.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(audit_logs.router)
