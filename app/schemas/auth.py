"""Authentication and user Pydantic schemas.

Covers user registration, login, JWT token payloads, and user
response serialization.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.enums import UserRole


class UserCreate(BaseModel):
    """Payload for registering a new user.

    Attributes:
        username: Desired username (3-50 characters).
        email: Valid email address.
        password: Plain-text password (min 8 characters).
        role: Optional role assignment (defaults to USER).
    """

    username: str = Field(min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(description="Valid email address")
    password: str = Field(min_length=8, max_length=128, description="Plain-text password")
    role: UserRole = Field(default=UserRole.USER, description="User role")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Ensure username contains only alphanumeric characters and underscores."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must contain only letters, digits, and underscores")
        return v.strip()


class UserLogin(BaseModel):
    """Payload for user login.

    Attributes:
        username: Registered username.
        password: Plain-text password.
    """

    username: str = Field(min_length=1, description="Username")
    password: str = Field(min_length=1, description="Password")


class UserResponse(BaseModel):
    """Serialized user for API responses (no password).

    Attributes:
        id: User primary key.
        username: Username.
        email: Email address.
        role: Assigned role.
        is_active: Account active flag.
        created_at: Registration timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT token pair returned after successful authentication.

    Attributes:
        access_token: Short-lived access JWT.
        refresh_token: Long-lived refresh JWT.
        token_type: Bearer (always).
    """

    access_token: str = Field(description="Short-lived access JWT")
    refresh_token: str = Field(description="Long-lived refresh JWT")
    token_type: str = Field(default="bearer", description="Token type")


class TokenPayload(BaseModel):
    """Decoded JWT payload used internally for authorization.

    Attributes:
        sub: Subject — the username.
        user_id: Numeric user ID.
        role: User role.
        exp: Expiration timestamp (epoch seconds).
        type: Token type ('access' or 'refresh').
    """

    sub: str = Field(description="Subject (username)")
    user_id: int = Field(description="Numeric user ID")
    role: UserRole = Field(description="User role")
    exp: int = Field(description="Expiration epoch seconds")
    type: str = Field(description="Token type: 'access' or 'refresh'")


class RefreshTokenRequest(BaseModel):
    """Payload for refreshing an access token.

    Attributes:
        refresh_token: A valid, non-expired refresh JWT.
    """

    refresh_token: str = Field(description="Valid refresh JWT")
