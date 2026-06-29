"""Repository for User entity data access."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for ``User`` entity CRUD and lookup operations.

    Extends ``BaseRepository`` with user-specific queries such as
    lookup by username or email.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the UserRepository.

        Args:
            db: The active SQLAlchemy session.
        """
        super().__init__(User, db)

    def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by their unique username.

        Args:
            username: The username to search for.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.
        """
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by their unique email address.

        Args:
            email: The email address to search for.

        Returns:
            The matching ``User`` instance, or ``None`` if not found.
        """
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()
