"""Tests for authentication endpoints: register, login, refresh, /me."""


# ─── Registration ─────────────────────────────────────────────────────────────


def test_register_user(client):
    """POST /auth/register creates a user and returns 201."""
    response = client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@test.com",
        "password": "testpass123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@test.com"
    assert "id" in data
    # Password hash must never be returned
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_returns_user_role_by_default(client):
    """New registrations default to the 'user' role."""
    response = client.post("/api/v1/auth/register", json={
        "username": "newbie",
        "email": "newbie@test.com",
        "password": "pass1234",
    })
    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_register_duplicate_username(client):
    """Registering with an existing username returns 409."""
    payload_1 = {
        "username": "dup",
        "email": "dup1@test.com",
        "password": "pass1234",
    }
    payload_2 = {
        "username": "dup",
        "email": "dup2@test.com",
        "password": "pass1234",
    }
    client.post("/api/v1/auth/register", json=payload_1)
    response = client.post("/api/v1/auth/register", json=payload_2)
    assert response.status_code == 409


def test_register_duplicate_email(client):
    """Registering with an existing email returns 409."""
    payload_1 = {
        "username": "user1",
        "email": "same@test.com",
        "password": "pass1234",
    }
    payload_2 = {
        "username": "user2",
        "email": "same@test.com",
        "password": "pass1234",
    }
    client.post("/api/v1/auth/register", json=payload_1)
    response = client.post("/api/v1/auth/register", json=payload_2)
    assert response.status_code == 409


def test_register_invalid_email(client):
    """Registering with an invalid email returns 422."""
    response = client.post("/api/v1/auth/register", json={
        "username": "bademail",
        "email": "not-an-email",
        "password": "pass1234",
    })
    assert response.status_code == 422


def test_register_missing_password(client):
    """Registering without a password returns 422."""
    response = client.post("/api/v1/auth/register", json={
        "username": "nopw",
        "email": "nopw@test.com",
    })
    assert response.status_code == 422


# ─── Login ────────────────────────────────────────────────────────────────────


def test_login(client):
    """Successful login returns access and refresh tokens."""
    client.post("/api/v1/auth/register", json={
        "username": "loginuser",
        "email": "login@test.com",
        "password": "pass1234",
    })
    response = client.post("/api/v1/auth/login", data={
        "username": "loginuser",
        "password": "pass1234",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Login with wrong password returns 401."""
    client.post("/api/v1/auth/register", json={
        "username": "wrongpw",
        "email": "wp@test.com",
        "password": "correct1",
    })
    response = client.post("/api/v1/auth/login", data={
        "username": "wrongpw",
        "password": "wrong",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Login with a username that doesn't exist returns 401."""
    response = client.post("/api/v1/auth/login", data={
        "username": "ghost",
        "password": "doesntmatter",
    })
    assert response.status_code == 401


# ─── Token Refresh ────────────────────────────────────────────────────────────


def test_refresh_token(client):
    """Exchanging a valid refresh token returns new token pair."""
    client.post("/api/v1/auth/register", json={
        "username": "refreshuser",
        "email": "refresh@test.com",
        "password": "pass1234",
    })
    login_resp = client.post("/api/v1/auth/login", data={
        "username": "refreshuser",
        "password": "pass1234",
    })
    refresh_token = login_resp.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_with_invalid_token(client):
    """Using an invalid refresh token returns 401."""
    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "this.is.not.a.valid.jwt",
    })
    assert response.status_code == 401


# ─── Current User ─────────────────────────────────────────────────────────────


def test_get_me(client, auth_headers):
    """GET /auth/me returns the authenticated user's profile."""
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


def test_get_me_without_token(client):
    """GET /auth/me without a token returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token(client):
    """GET /auth/me with a garbage token returns 401."""
    headers = {"Authorization": "Bearer garbage.token.here"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


# ─── Protected Endpoints ─────────────────────────────────────────────────────


def test_protected_endpoint_without_token(client):
    """Accessing a protected endpoint without auth returns 401."""
    response = client.post("/api/v1/customers/", json={
        "name": "Test Customer",
        "email": "cust@test.com",
        "phone": "1234567890",
    })
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token(client, auth_headers):
    """Accessing a protected endpoint with a valid token succeeds."""
    response = client.get("/api/v1/customers/", headers=auth_headers)
    assert response.status_code == 200
