"""User ORM model for authentication and authorization.

Stores credentials and role information. Passwords are stored as
bcrypt hashes — never in plain text.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import UserRole
from app.database.base import Base


class User(Base):
    """Application user with role-based access control.

    Attributes:
        id: Primary key.
        username: Unique login identifier.
        email: Unique email address.
        hashed_password: Bcrypt hash of the user's password.
        role: Authorization role (ADMIN, MANAGER, USER).
        is_active: Soft-delete / disable flag.
        created_at: Row creation timestamp (server-side).
        updated_at: Last modification timestamp (auto-updated).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role={self.role.value})>"
