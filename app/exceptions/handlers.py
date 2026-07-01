"""FastAPI exception handlers for the OMS domain exception hierarchy.

Each domain exception is mapped to the appropriate HTTP status code and
returned in a consistent JSON envelope::

    {
        "error": {
            "code": "ENTITY_NOT_FOUND",
            "message": "Product with identifier '42' not found",
            "details": {"entity": "Product", "identifier": "42"}
        }
    }
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.exceptions.base import (
    AuthenticationError,
    AuthorizationError,
    BusinessValidationError,
    ConflictError,
    EntityNotFoundError,
    InsufficientStockError,
    InvalidStateTransitionError,
    OMSException,
    PaymentError,
)

# Mapping from exception class to HTTP status code.  Order matters: more
# specific subclasses are checked first by Python's MRO, but FastAPI
# dispatches on the *exact* registered type, so we register each leaf.
_EXCEPTION_STATUS_MAP: dict[type[OMSException], int] = {
    EntityNotFoundError: 404,
    AuthenticationError: 401,
    AuthorizationError: 403,
    PaymentError: 402,
    ConflictError: 409,
    InvalidStateTransitionError: 409,
    InsufficientStockError: 409,
    BusinessValidationError: 422,
}


def _build_error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    """Build a uniform JSON error response.

    Args:
        status_code: HTTP status code.
        code: Machine-readable error code.
        message: Human-readable error description.
        details: Optional extra context.

    Returns:
        JSONResponse with the standard error envelope.
    """
    payload: dict = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


# ------------------------------------------------------------------
# Handler functions
# ------------------------------------------------------------------

def _handle_oms_exception(_request: Request, exc: OMSException) -> JSONResponse:
    """Handle any ``OMSException`` subclass.

    Looks up the HTTP status code from ``_EXCEPTION_STATUS_MAP``,
    falling back to **500** for unmapped subclasses.
    """
    status_code = _EXCEPTION_STATUS_MAP.get(type(exc), 500)

    # Walk the MRO for subclasses not directly in the map (e.g.
    # InvalidCouponError → BusinessValidationError → 422).
    if type(exc) not in _EXCEPTION_STATUS_MAP:
        for parent in type(exc).__mro__:
            if parent in _EXCEPTION_STATUS_MAP:
                status_code = _EXCEPTION_STATUS_MAP[parent]
                break

    if status_code >= 500:
        logger.error(
            "Unhandled OMS exception: {code} – {message}",
            code=exc.code,
            message=exc.message,
        )
    else:
        logger.warning(
            "Domain error: {code} – {message}",
            code=exc.code,
            message=exc.message,
        )

    return _build_error_response(
        status_code=status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


def _handle_validation_error(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation errors.

    Reformats the built-in error list into the standard envelope at
    HTTP **422**.
    """
    errors = exc.errors()
    logger.warning("Request validation failed: {errors}", errors=errors)

    # Flatten Pydantic errors into a concise list.
    field_errors: list[dict] = []
    for err in errors:
        field_errors.append(
            {
                "field": " → ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
        )

    return _build_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": field_errors},
    )


def _handle_generic_exception(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all handler for unexpected / unhandled exceptions.

    Logs the full traceback and returns a generic **500** response so
    that internal details are never leaked to the client.
    """
    logger.exception("Unhandled exception: {exc}", exc=str(exc))
    return _build_error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
    )


def _handle_integrity_error(
    _request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    """Handle SQLAlchemy integrity errors.

    Converts unique constraint violations into a domain ``ConflictError``
    response so repeated or concurrent duplicate inserts do not expose a
    raw database exception.
    """
    logger.warning(
        "Database integrity error: {error}",
        error=str(exc.orig) if exc.orig is not None else str(exc),
    )

    # A generic 409 Conflict envelope without leaking raw SQL details.
    return _build_error_response(
        status_code=409,
        code="CONFLICT",
        message="A database conflict occurred. The requested operation may already exist or violate a uniqueness constraint.",
        details={"error": "integrity_constraint_violation"},
    )


# ------------------------------------------------------------------
# Registration helper
# ------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application.

    Call this once during application startup (in ``create_app``).

    Args:
        app: The FastAPI application instance.
    """
    # Specific database integrity errors are translated into a 409 Conflict
    # response so concurrent duplicate inserts do not crash the application.
    app.add_exception_handler(IntegrityError, _handle_integrity_error)  # type: ignore[arg-type]

    # Domain exceptions – register the base class; the handler walks
    # the MRO to resolve the correct status code.
    app.add_exception_handler(OMSException, _handle_oms_exception)  # type: ignore[arg-type]

    # Pydantic / FastAPI validation errors
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]

    # Generic fallback
    app.add_exception_handler(Exception, _handle_generic_exception)  # type: ignore[arg-type]
