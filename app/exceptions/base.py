"""Custom exception hierarchy for the Order Management System.

Every domain-level error inherits from ``OMSException`` and carries a
machine-readable ``code`` plus optional ``details``.  Exception handlers
(see ``app.exceptions.handlers``) map each subclass to the correct HTTP
status code so that services never import FastAPI directly.
"""

from typing import Any


class OMSException(Exception):
    """Base exception for all OMS domain errors.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code (e.g. ``ENTITY_NOT_FOUND``).
        details: Optional structured context for debugging / API consumers.
    """

    def __init__(
        self,
        message: str,
        code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# 404 – Not Found
# ---------------------------------------------------------------------------

class EntityNotFoundError(OMSException):
    """Raised when a requested entity does not exist.

    Maps to HTTP **404 Not Found**.
    """

    def __init__(self, entity: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity} with identifier '{identifier}' not found",
            code="ENTITY_NOT_FOUND",
            details={"entity": entity, "identifier": str(identifier)},
        )


# ---------------------------------------------------------------------------
# 409 – Conflict
# ---------------------------------------------------------------------------

class ConflictError(OMSException):
    """Raised on duplicate or conflicting resource creation.

    Maps to HTTP **409 Conflict**.  Typical triggers include duplicate
    email addresses, duplicate SKUs, or concurrent modifications.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            details=details,
        )


class InvalidStateTransitionError(OMSException):
    """Raised when a status transition violates the state machine.

    Maps to HTTP **409 Conflict**.
    """

    def __init__(self, entity: str, current_status: str, target_status: str) -> None:
        super().__init__(
            message=(
                f"Cannot transition {entity} from '{current_status}' "
                f"to '{target_status}'"
            ),
            code="INVALID_STATE_TRANSITION",
            details={
                "entity": entity,
                "current_status": current_status,
                "target_status": target_status,
            },
        )


class InsufficientStockError(OMSException):
    """Raised when requested quantity exceeds available inventory.

    Maps to HTTP **409 Conflict**.
    """

    def __init__(
        self,
        product_id: int,
        sku: str,
        warehouse: str,
        requested: int,
        available: int,
    ) -> None:
        super().__init__(
            message=(
                f"Insufficient stock for product '{sku}' in warehouse "
                f"'{warehouse}': requested {requested}, available {available}"
            ),
            code="INSUFFICIENT_STOCK",
            details={
                "product_id": product_id,
                "sku": sku,
                "warehouse": warehouse,
                "requested": requested,
                "available": available,
            },
        )


# ---------------------------------------------------------------------------
# 422 – Business Validation
# ---------------------------------------------------------------------------

class BusinessValidationError(OMSException):
    """Raised when a business rule is violated.

    Maps to HTTP **422 Unprocessable Entity**.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="BUSINESS_VALIDATION_ERROR",
            details=details,
        )


class InvalidCouponError(BusinessValidationError):
    """Raised when a coupon fails validation.

    Maps to HTTP **422 Unprocessable Entity**.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
        self.code = "INVALID_COUPON"


class InvalidOrderError(BusinessValidationError):
    """Raised when an order fails validation rules.

    Maps to HTTP **422 Unprocessable Entity**.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
        self.code = "INVALID_ORDER"


# ---------------------------------------------------------------------------
# 401 – Authentication
# ---------------------------------------------------------------------------

class AuthenticationError(OMSException):
    """Raised on authentication failures (invalid credentials, expired tokens).

    Maps to HTTP **401 Unauthorized**.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details,
        )


# ---------------------------------------------------------------------------
# 403 – Authorization
# ---------------------------------------------------------------------------

class AuthorizationError(OMSException):
    """Raised when the user lacks required permissions.

    Maps to HTTP **403 Forbidden**.
    """

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            details=details,
        )


# ---------------------------------------------------------------------------
# 402 – Payment
# ---------------------------------------------------------------------------

class PaymentError(OMSException):
    """Raised on payment processing failures.

    Maps to HTTP **402 Payment Required**.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="PAYMENT_ERROR",
            details=details,
        )
