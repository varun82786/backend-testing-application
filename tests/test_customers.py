"""Tests for customer CRUD endpoints."""

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────


CUSTOMER_PAYLOAD = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "+1-555-0101",
    "address": "123 Main St, Springfield",
    "loyalty_points": 0,
}


def _create_customer(client, headers, **overrides):
    """Helper to create a customer and return the response."""
    payload = {**CUSTOMER_PAYLOAD, **overrides}
    return client.post("/api/v1/customers/", json=payload, headers=headers)


# ─── Create ───────────────────────────────────────────────────────────────────


def test_create_customer(client, auth_headers):
    """POST /customers/ creates a customer and returns 201."""
    response = _create_customer(client, auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice Smith"
    assert data["email"] == "alice@example.com"
    assert data["phone"] == "+1-555-0101"
    assert data["loyalty_points"] == 0
    assert "id" in data
    assert "created_at" in data


def test_create_customer_minimal(client, auth_headers):
    """Creating a customer without optional fields succeeds."""
    response = client.post("/api/v1/customers/", json={
        "name": "Bob",
        "email": "bob@example.com",
        "phone": "9876543210",
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["address"] is None
    assert data["loyalty_points"] == 0


def test_create_customer_invalid_email(client, auth_headers):
    """Creating a customer with invalid email returns 422."""
    response = _create_customer(client, auth_headers, email="bad-email")
    assert response.status_code == 422


def test_create_customer_empty_name(client, auth_headers):
    """Creating a customer with an empty name returns 422."""
    response = _create_customer(client, auth_headers, name="")
    assert response.status_code == 422


def test_create_customer_invalid_phone(client, auth_headers):
    """Creating a customer with alphabetic phone returns 422."""
    response = _create_customer(client, auth_headers, phone="abc-xyz")
    assert response.status_code == 422


# ─── Duplicate Detection ─────────────────────────────────────────────────────


def test_duplicate_email(client, auth_headers):
    """Creating two customers with the same email returns 409."""
    _create_customer(client, auth_headers, email="dupe@example.com", phone="1111111111")
    response = _create_customer(
        client, auth_headers, email="dupe@example.com", phone="2222222222",
        name="Different Name",
    )
    assert response.status_code == 409


def test_duplicate_phone(client, auth_headers):
    """Creating two customers with the same phone returns 409."""
    _create_customer(client, auth_headers, phone="3333333333", email="one@example.com")
    response = _create_customer(
        client, auth_headers, phone="3333333333", email="two@example.com",
        name="Different Name",
    )
    assert response.status_code == 409


# ─── Read ─────────────────────────────────────────────────────────────────────


def test_get_customer(client, auth_headers):
    """GET /customers/{id} returns the correct customer."""
    create_resp = _create_customer(client, auth_headers)
    customer_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == customer_id
    assert response.json()["name"] == "Alice Smith"


def test_get_nonexistent_customer(client, auth_headers):
    """GET /customers/{id} for a missing customer returns 404."""
    response = client.get("/api/v1/customers/99999", headers=auth_headers)
    assert response.status_code == 404


def test_list_customers_empty(client, auth_headers):
    """GET /customers/ with no data returns an empty paginated list."""
    response = client.get("/api/v1/customers/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_customers_paginated(client, auth_headers):
    """GET /customers/ returns properly paginated results."""
    # Create 5 customers
    for i in range(5):
        _create_customer(
            client, auth_headers,
            name=f"Customer {i}",
            email=f"c{i}@example.com",
            phone=f"555000{i:04d}",
        )

    # Request page 1 with page_size=2
    response = client.get(
        "/api/v1/customers/?page=1&page_size=2",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Request page 3 (should have 1 item)
    response = client.get(
        "/api/v1/customers/?page=3&page_size=2",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1


# ─── Update ───────────────────────────────────────────────────────────────────


def test_update_customer(client, auth_headers):
    """PUT /customers/{id} updates the customer fields."""
    create_resp = _create_customer(client, auth_headers)
    customer_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/customers/{customer_id}",
        json={"name": "Alice Updated", "loyalty_points": 100},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Alice Updated"
    assert data["loyalty_points"] == 100
    # Unchanged fields should persist
    assert data["email"] == "alice@example.com"


def test_update_nonexistent_customer(client, auth_headers):
    """PUT /customers/{id} for a missing customer returns 404."""
    response = client.put(
        "/api/v1/customers/99999",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ─── Delete ───────────────────────────────────────────────────────────────────


def test_delete_customer(client, auth_headers):
    """DELETE /customers/{id} removes the customer."""
    create_resp = _create_customer(client, auth_headers)
    customer_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify it's gone
    get_resp = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


def test_delete_nonexistent_customer(client, auth_headers):
    """DELETE /customers/{id} for a missing customer returns 404."""
    response = client.delete(
        "/api/v1/customers/99999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ─── Role-Based Access ───────────────────────────────────────────────────────


def test_regular_user_cannot_create_customer(client, user_headers):
    """Regular users cannot create customers (403)."""
    response = client.post("/api/v1/customers/", json={
        "name": "Forbidden",
        "email": "forbidden@example.com",
        "phone": "1234567890",
    }, headers=user_headers)
    assert response.status_code == 403


def test_regular_user_can_list_customers(client, user_headers):
    """Regular users can list customers (read access)."""
    response = client.get("/api/v1/customers/", headers=user_headers)
    assert response.status_code == 200


def test_manager_can_create_customer(client, manager_headers):
    """Managers can create customers."""
    response = client.post("/api/v1/customers/", json={
        "name": "Manager Created",
        "email": "mgr-created@example.com",
        "phone": "5550001234",
    }, headers=manager_headers)
    assert response.status_code == 201


def test_manager_cannot_delete_customer(client, auth_headers, manager_headers):
    """Managers cannot delete customers (admin-only)."""
    # Admin creates
    create_resp = _create_customer(client, auth_headers)
    customer_id = create_resp.json()["id"]

    # Manager tries to delete
    response = client.delete(
        f"/api/v1/customers/{customer_id}",
        headers=manager_headers,
    )
    assert response.status_code == 403
