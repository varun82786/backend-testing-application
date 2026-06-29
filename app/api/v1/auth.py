"""Authentication API routes.

Handles user registration, login (JWT issuance), token refresh,
and current-user profile retrieval.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.schemas.common import ErrorResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with the provided credentials and role.",
    responses={
        409: {"model": ErrorResponse, "description": "Username or email already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account.

    Args:
        data: User registration payload containing username, email,
            password, and optional role.
        db: Database session (injected).

    Returns:
        The newly created user profile.
    """
    service = AuthService(db)
    user = service.register(data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain tokens",
    description=(
        "Authenticate with username and password to receive a JWT access "
        "token and refresh token. Uses OAuth2 password flow for Swagger UI "
        "compatibility."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
    },
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return JWT tokens.

    Uses ``OAuth2PasswordRequestForm`` so the Swagger UI Authorize
    dialog works out of the box.

    Args:
        form_data: OAuth2 form with ``username`` and ``password`` fields.
        db: Database session (injected).

    Returns:
        Access and refresh JWT tokens.
    """
    service = AuthService(db)
    credentials = UserLogin(username=form_data.username, password=form_data.password)
    tokens = service.login(credentials)
    return TokenResponse(**tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an access token",
    description="Exchange a valid refresh token for a new access/refresh token pair.",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
)
def refresh_token(
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Refresh an expired access token.

    Args:
        body: Request body containing the refresh token.
        db: Database session (injected).

    Returns:
        A new access and refresh token pair.
    """
    service = AuthService(db)
    tokens = service.refresh_token(body.refresh_token)
    return TokenResponse(**tokens)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve the profile of the currently authenticated user.",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return the authenticated user's profile.

    Args:
        current_user: The authenticated user (injected by auth dependency).

    Returns:
        The current user's profile data.
    """
    return UserResponse.model_validate(current_user)
