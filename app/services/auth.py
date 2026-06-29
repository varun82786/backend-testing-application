"""Authentication service.

Handles user registration, login, and JWT token refresh.  Password
hashing uses bcrypt via ``passlib`` and tokens are created with
``PyJWT`` — see ``app.auth`` sub-modules.

Design notes:
    * Duplicate username / email checks happen *before* the INSERT
      to provide clear error messages.
    * Audit log entries are written for both ``REGISTER`` and
      ``LOGIN`` actions.
    * Refresh token rotation: a refresh request issues *both* a new
      access token and a new refresh token (sliding window).
"""

from loguru import logger
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.passwords import hash_password, verify_password
from app.core.enums import AuditAction
from app.exceptions.base import AuthenticationError, ConflictError
from app.models import User
from app.repositories.user import UserRepository
from app.schemas.auth import UserCreate, UserLogin
from app.services.audit import AuditService


class AuthService:
    """Service for authentication and user management.

    Args:
        db: The active SQLAlchemy session.
    """

    def __init__(self, db: Session) -> None:
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db)
        self.db = db

    def register(self, data: UserCreate) -> User:
        """Register a new user.

        Validates that neither the username nor email is already in
        use, hashes the password, persists the user, and creates an
        audit log entry.

        Args:
            data: Validated registration payload.

        Returns:
            The newly created ``User`` instance.

        Raises:
            ConflictError: If the username or email is already taken.
        """
        # Check for duplicate username.
        if self.user_repo.get_by_username(data.username):
            raise ConflictError(
                message=f"Username '{data.username}' is already taken",
                details={"field": "username", "value": data.username},
            )

        # Check for duplicate email.
        if self.user_repo.get_by_email(data.email):
            raise ConflictError(
                message=f"Email '{data.email}' is already registered",
                details={"field": "email", "value": data.email},
            )

        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
            role=data.role,
            is_active=True,
        )
        created_user = self.user_repo.create(user)

        logger.info(
            "User registered: username={username} role={role}",
            username=created_user.username,
            role=created_user.role.value,
        )

        self.audit_service.log(
            entity="User",
            entity_id=created_user.id,
            action=AuditAction.REGISTER,
            new_value=created_user,
            performed_by=created_user.username,
        )

        return created_user

    def login(self, data: UserLogin) -> dict:
        """Authenticate a user and return JWT tokens.

        Verifies that the username exists, the account is active, and
        the password matches.  On success returns an access / refresh
        token pair.

        Args:
            data: Validated login payload.

        Returns:
            A dict containing ``access_token``, ``refresh_token``, and
            ``token_type``.

        Raises:
            AuthenticationError: If credentials are invalid or the
                account is disabled.
        """
        user = self.user_repo.get_by_username(data.username)
        if not user:
            raise AuthenticationError(
                message="Invalid username or password",
                details={"reason": "user_not_found"},
            )

        if not user.is_active:
            raise AuthenticationError(
                message="Account is disabled",
                details={"reason": "account_disabled"},
            )

        if not verify_password(data.password, user.hashed_password):
            raise AuthenticationError(
                message="Invalid username or password",
                details={"reason": "invalid_password"},
            )

        access_token = create_access_token(
            subject=user.username,
            user_id=user.id,
            role=user.role.value,
        )
        refresh_token = create_refresh_token(
            subject=user.username,
            user_id=user.id,
            role=user.role.value,
        )

        logger.info("User logged in: username={username}", username=user.username)

        self.audit_service.log(
            entity="User",
            entity_id=user.id,
            action=AuditAction.LOGIN,
            performed_by=user.username,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    def refresh_token(self, refresh_token_str: str) -> dict:
        """Issue a new token pair from a valid refresh token.

        Decodes the supplied refresh JWT, verifies that its ``type``
        claim is ``"refresh"``, looks up the user, and issues fresh
        access + refresh tokens (sliding window rotation).

        Args:
            refresh_token_str: The raw refresh JWT string.

        Returns:
            A dict containing ``access_token``, ``refresh_token``, and
            ``token_type``.

        Raises:
            AuthenticationError: If the token is invalid, expired, not
                a refresh token, or the user no longer exists / is
                disabled.
        """
        payload = decode_token(refresh_token_str)

        if payload.get("type") != "refresh":
            raise AuthenticationError(
                message="Invalid token type — expected refresh token",
                details={"reason": "invalid_token_type"},
            )

        user_id: int | None = payload.get("user_id")
        if user_id is None:
            raise AuthenticationError(
                message="Token payload missing user_id",
                details={"reason": "missing_user_id"},
            )

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError(
                message="User not found",
                details={"reason": "user_not_found"},
            )

        if not user.is_active:
            raise AuthenticationError(
                message="Account is disabled",
                details={"reason": "account_disabled"},
            )

        access_token = create_access_token(
            subject=user.username,
            user_id=user.id,
            role=user.role.value,
        )
        new_refresh_token = create_refresh_token(
            subject=user.username,
            user_id=user.id,
            role=user.role.value,
        )

        logger.info(
            "Token refreshed for user: username={username}",
            username=user.username,
        )

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }
