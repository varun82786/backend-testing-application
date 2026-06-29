"""Shared FastAPI dependencies for authentication and database access.

These dependencies are designed to be used with ``Depends()`` in route
definitions::

    @router.get("/me")
    def read_current_user(
        user: User = Depends(get_current_active_user),
    ) -> UserRead:
        ...
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.core.enums import UserRole
from app.database.session import get_db
from app.exceptions.base import AuthenticationError

# The ``tokenUrl`` must match the login endpoint so that the Swagger UI
# "Authorize" dialog can request tokens automatically.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> "User":
    """Decode the JWT and return the corresponding ``User`` instance.

    Args:
        token: The bearer token extracted from the ``Authorization``
            header (injected by ``oauth2_scheme``).
        db: The database session (injected by ``get_db``).

    Returns:
        The authenticated ``User`` ORM object.

    Raises:
        AuthenticationError: If the token is invalid, expired, or the
            user no longer exists.
    """
    # Import here to avoid circular dependency with models package
    from app.models.user import User  # noqa: WPS433

    payload = decode_token(token)

    # Ensure this is an access token, not a refresh token.
    token_type: str | None = payload.get("type")
    if token_type != "access":
        raise AuthenticationError(
            message="Invalid token type",
            details={"expected": "access", "got": token_type},
        )

    user_id: int | None = payload.get("user_id")
    if user_id is None:
        raise AuthenticationError(
            message="Token payload missing user_id",
        )

    user: User | None = db.get(User, user_id)
    if user is None:
        raise AuthenticationError(
            message="User not found",
            details={"user_id": user_id},
        )

    return user


def get_current_active_user(
    current_user: "User" = Depends(get_current_user),
) -> "User":
    """Ensure the authenticated user account is active.

    Args:
        current_user: The user resolved by ``get_current_user``
            (injected by FastAPI).

    Returns:
        The active ``User`` ORM object.

    Raises:
        AuthenticationError: If the user account is deactivated.
    """
    if not current_user.is_active:
        raise AuthenticationError(
            message="User account is deactivated",
            details={"user_id": current_user.id},
        )
    return current_user
