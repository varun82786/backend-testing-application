"""Common / shared Pydantic schemas.

Provides reusable primitives for pagination, error envelopes, and
generic success responses used across all API endpoints.
"""

from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ── Pagination ─────────────────────────────────────────────────────


class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints.

    Attributes:
        page: 1-based page index.
        page_size: Number of items per page (max 100).
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for paginated list results.

    Attributes:
        items: The page of results.
        total: Total number of matching records.
        page: Current page number.
        page_size: Requested page size.
        total_pages: Computed total number of pages.
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int = Field(ge=0, description="Total matching records")
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0, description="Computed total pages")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[T]:
        """Factory that computes ``total_pages`` automatically.

        Args:
            items: The current page of results.
            total: Total matching records across all pages.
            page: Current 1-based page index.
            page_size: Number of items requested per page.

        Returns:
            A fully-populated PaginatedResponse instance.
        """
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


# ── Error / Success Envelopes ─────────────────────────────────────


class ErrorDetail(BaseModel):
    """Structured error information.

    Attributes:
        code: Machine-readable error code (e.g. 'VALIDATION_ERROR').
        message: Human-readable error message.
        details: Optional additional context.
    """

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(
        default=None, description="Additional error context"
    )


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all API error handlers.

    Attributes:
        error: Structured error detail.
    """

    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Generic success envelope for operations without a domain body.

    Attributes:
        message: Human-readable success message.
        data: Optional payload.
    """

    message: str = Field(description="Human-readable success message")
    data: dict | None = Field(default=None, description="Optional payload")
