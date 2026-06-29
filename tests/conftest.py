"""Shared pytest fixtures for the OMS test suite.

Provides:
    - An in-memory SQLite database that is created and dropped per test.
    - A FastAPI TestClient wired to the test database session.
    - Pre-built admin user, JWT token, and auth header fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import create_app
from app.auth.passwords import hash_password
from app.models import User
from app.core.enums import UserRole
from app.auth.jwt import create_access_token

# Use in-memory SQLite for tests — fast, isolated, no disk I/O.
# StaticPool ensures ALL connections share the same :memory: database
# so tables created via create_all are visible to every session.
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable foreign keys for SQLite (mirrors production config)
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
def db_session():
    """Yield a clean database session per test.

    Creates all tables before the test and drops them after,
    guaranteeing full isolation between tests.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Yield a FastAPI TestClient wired to the test database.

    Overrides the ``get_db`` dependency so all requests use the
    in-memory test session instead of the real database.
    """
    app = create_app()

    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_user(db_session):
    """Create and return an admin user in the test database."""
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manager_user(db_session):
    """Create and return a manager user in the test database."""
    user = User(
        username="manager",
        email="manager@test.com",
        hashed_password=hash_password("manager123"),
        role=UserRole.MANAGER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session):
    """Create and return a regular user in the test database."""
    user = User(
        username="regularuser",
        email="user@test.com",
        hashed_password=hash_password("user123"),
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Return a valid JWT access token for the admin user."""
    return create_access_token(
        subject=admin_user.username,
        user_id=admin_user.id,
        role=admin_user.role.value,
    )


@pytest.fixture
def manager_token(manager_user):
    """Return a valid JWT access token for the manager user."""
    return create_access_token(
        subject=manager_user.username,
        user_id=manager_user.id,
        role=manager_user.role.value,
    )


@pytest.fixture
def user_token(regular_user):
    """Return a valid JWT access token for the regular user."""
    return create_access_token(
        subject=regular_user.username,
        user_id=regular_user.id,
        role=regular_user.role.value,
    )


@pytest.fixture
def auth_headers(admin_token):
    """Return Authorization headers with the admin JWT token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def manager_headers(manager_token):
    """Return Authorization headers with the manager JWT token."""
    return {"Authorization": f"Bearer {manager_token}"}


@pytest.fixture
def user_headers(user_token):
    """Return Authorization headers with the regular user JWT token."""
    return {"Authorization": f"Bearer {user_token}"}
