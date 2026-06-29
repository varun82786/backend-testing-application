"""Bug injection helper functions.

Each function in this module encapsulates a *single* injectable defect.
Service-layer code calls these helpers instead of inline ``if`` checks,
keeping bug-injection logic centralised and easy to audit.

Design decision: plain functions (not decorators) for simplicity and
explicit call-site visibility.
"""

from decimal import Decimal

from app.bugs.registry import bug_registry


def calculate_gst(subtotal: Decimal, gst_percentage: Decimal) -> Decimal:
    """Calculate GST amount, with optional intentional miscalculation.

    When the ``WRONG_GST`` bug is active the effective rate is inflated
    by an additional 5 percentage points.

    Args:
        subtotal: The pre-tax amount.
        gst_percentage: The intended GST rate (e.g. ``Decimal("18")``
            for 18 %).

    Returns:
        The computed GST amount.
    """
    if bug_registry.is_active("WRONG_GST"):
        return subtotal * (gst_percentage + Decimal("5")) / Decimal("100")
    return subtotal * gst_percentage / Decimal("100")


def should_check_duplicate_payment() -> bool:
    """Return whether duplicate-payment validation should run.

    When the ``DUPLICATE_PAYMENT`` bug is active the check is
    intentionally skipped, allowing the same transaction to be
    processed more than once.

    Returns:
        ``True`` if the check should be performed, ``False`` if
        intentionally disabled.
    """
    return not bug_registry.is_active("DUPLICATE_PAYMENT")


def should_check_stock_negative() -> bool:
    """Return whether negative-inventory validation should run.

    When the ``NEGATIVE_INVENTORY`` bug is active, stock levels are
    allowed to drop below zero.

    Returns:
        ``True`` if the check should be performed, ``False`` if
        intentionally disabled.
    """
    return not bug_registry.is_active("NEGATIVE_INVENTORY")


def should_create_audit_log() -> bool:
    """Return whether audit log entries should be created.

    When the ``SKIP_AUDIT_LOG`` bug is active, audit logging is
    silently suppressed.

    Returns:
        ``True`` if audit logs should be written, ``False`` if
        intentionally suppressed.
    """
    return not bug_registry.is_active("SKIP_AUDIT_LOG")


def should_check_payment_before_shipment() -> bool:
    """Return whether payment verification is required before shipping.

    When the ``SHIPMENT_WITHOUT_PAYMENT`` bug is active, orders may be
    shipped even when no successful payment exists.

    Returns:
        ``True`` if the check should be performed, ``False`` if
        intentionally disabled.
    """
    return not bug_registry.is_active("SHIPMENT_WITHOUT_PAYMENT")
