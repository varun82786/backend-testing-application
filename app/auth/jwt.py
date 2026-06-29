"""JWT token creation and decoding using PyJWT.

This module deliberately avoids ``python-jose`` (which has known CVEs)
and uses ``PyJWT`` instead.  Tokens carry the following custom claims:

    * ``sub``  – the subject (typically the user's email).
    * ``user_id`` – the database primary key.
    * ``role`` – the user's role (admin / manager / user).
    * ``type`` – ``"access"`` or ``"refresh"``.
"""

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from app.exceptions.base import AuthenticationError


def create_access_token(subject: str, user_id: int, role: str) -> str:
    """Create a short-lived JWT access token.

    Args:
        subject: Token subject (e.g. the user's email).
        user_id: The user's database primary key.
        role: The user's role value.

    Returns:
        An encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict = {
        "sub": subject,
        "user_id": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(subject: str, user_id: int, role: str) -> str:
    """Create a long-lived JWT refresh token.

    Args:
        subject: Token subject (e.g. the user's email).
        user_id: The user's database primary key.
        role: The user's role value.

    Returns:
        An encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)

    payload: dict = {
        "sub": subject,
        "user_id": user_id,
        "role": role,
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The raw JWT string.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        AuthenticationError: If the token is expired, malformed, or
            otherwise invalid.
    """
    settings = get_settings()

    try:
        payload: dict = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(
            message="Token has expired",
            details={"reason": "expired"},
        )
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(
            message="Invalid token",
            details={"reason": str(exc)},
        )
