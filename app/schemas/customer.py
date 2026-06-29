"""Customer Pydantic schemas.

Provides create, update, and response schemas for customer
management endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerCreate(BaseModel):
    """Payload for creating a new customer.

    Attributes:
        name: Full name (1-100 characters).
        email: Valid email address.
        phone: Phone number.
        address: Optional shipping/billing address.
        loyalty_points: Initial loyalty points (defaults to 0).
    """

    name: str = Field(min_length=1, max_length=100, description="Customer full name")
    email: EmailStr = Field(description="Customer email")
    phone: str = Field(min_length=1, max_length=20, description="Phone number")
    address: str | None = Field(
        default=None, max_length=500, description="Shipping/billing address"
    )
    loyalty_points: int = Field(default=0, ge=0, description="Initial loyalty points")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Strip whitespace and ensure phone contains only digits, +, -, spaces, and parens."""
        v = v.strip()
        cleaned = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
        if not cleaned.isdigit():
            raise ValueError("Phone must contain only digits, +, -, spaces, and parentheses")
        return v


class CustomerUpdate(BaseModel):
    """Payload for partially updating an existing customer.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Updated name.
        email: Updated email.
        phone: Updated phone.
        address: Updated address.
        loyalty_points: Updated loyalty points.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    loyalty_points: int | None = Field(default=None, ge=0)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Strip whitespace and validate phone format when provided."""
        if v is None:
            return v
        v = v.strip()
        cleaned = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
        if not cleaned.isdigit():
            raise ValueError("Phone must contain only digits, +, -, spaces, and parentheses")
        return v


class CustomerResponse(BaseModel):
    """Serialized customer for API responses.

    Attributes:
        id: Primary key.
        name: Full name.
        email: Email address.
        phone: Phone number.
        address: Shipping/billing address.
        loyalty_points: Current loyalty points balance.
        created_at: Registration timestamp.
        updated_at: Last update timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    address: str | None
    loyalty_points: int
    created_at: datetime
    updated_at: datetime | None
