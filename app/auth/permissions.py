"""Role-based access control (RBAC) for FastAPI endpoints.

Usage::

    from app.auth.permissions import RoleChecker
    from app.core.enums import UserRole

    @router.post(
        "/products/",
        dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.MANAGER]))],
    )
    def create_product(...):
        ...

The ``RoleChecker`` is a callable class that acts as a FastAPI
dependency.  It resolves the current user via the standard auth
dependency chain and checks whether the user's role is among the
permitted roles.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.database.session import get_db
from app.exceptions.base import AuthenticationError, AuthorizationError

# Share the same OAuth2 scheme so token extraction works.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class RoleChecker:
    """FastAPI dependency that enforces role-based access.

    Instances are callable and designed to be used with ``Depends()``.
    Uses FastAPI's dependency injection for ``get_db`` so that
    dependency overrides (e.g. in tests) are respected.

    Attributes:
        allowed_roles: The set of roles that may access the endpoint.
    """

    def __init__(self, allowed_roles: list[UserRole]) -> None:
        """Initialise the checker with the permitted roles.

        Args:
            allowed_roles: Roles that are allowed to access the
                protected endpoint.
        """
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        token: str = Depends(_oauth2_scheme),
        db: Session = Depends(get_db),
    ) -> Any:
        """Verify that the current user has one of the allowed roles.

        Resolves the current user using the injected ``db`` session
        (respecting any dependency overrides), then checks the role.

        Args:
            token: The bearer token (injected by FastAPI).
            db: Database session (injected by FastAPI via ``get_db``).

        Returns:
            The authenticated user if authorised.

        Raises:
            AuthenticationError: If the token is invalid or the user
                is not found.
            AuthorizationError: If the user's role is not in
                ``allowed_roles``.
        """
        # Lazy import to break circular dependency chain.
        from app.api.deps import get_current_user  # noqa: WPS433

        # Use the DI-provided db and token so overrides work.
        current_user = get_current_user(token=token, db=db)

        if current_user.role not in self.allowed_roles:
            raise AuthorizationError(
                message=(
                    f"Role '{current_user.role.value}' is not permitted. "
                    f"Required: {[r.value for r in self.allowed_roles]}"
                ),
                details={
                    "user_role": current_user.role.value,
                    "required_roles": [r.value for r in self.allowed_roles],
                },
            )
        return current_user
