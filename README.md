# 🛒 Order Management System (OMS)

A **production-grade REST API** for managing the full order lifecycle — customers, products, inventory, orders, payments, shipments, coupons, and reporting. Built with FastAPI, SQLAlchemy 2.x, and Pydantic v2.

Includes **deliberate, configurable bug injection** for QA testing and training purposes.

---

## 📋 Table of Contents

- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [API Documentation](#-api-documentation)
- [Authentication Guide](#-authentication-guide)
- [API Endpoints](#-api-endpoints)
- [Bug Injection Guide](#-bug-injection-guide)
- [Testing Guide](#-testing-guide)

---

## 🛠 Tech Stack

| Category       | Technology                | Why                                              |
|----------------|---------------------------|--------------------------------------------------|
| Framework      | FastAPI 0.115             | Async-capable, auto-docs, type-safe              |
| ORM            | SQLAlchemy 2.x (sync)     | Mapped types, DeclarativeBase, mature ecosystem   |
| Validation     | Pydantic v2               | ConfigDict, field_validator, 5-17× faster         |
| Database       | SQLite + WAL mode         | Zero-config, file-based, great for demos          |
| Migrations     | Alembic 1.15              | Autogenerate, version control for schema          |
| Auth           | PyJWT + passlib\[bcrypt\] | No CVEs (unlike python-jose), industry standard   |
| Logging        | Loguru                    | Structured JSON logs, zero-config                 |
| Testing        | pytest + TestClient       | In-memory SQLite, fixture-driven                  |
| Server         | Uvicorn                   | ASGI, production-ready                            |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                          │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────────────┐ │
│  │Middleware │→ │  Routers   │→ │   Exception Handlers    │ │
│  │(Logging) │  │ (API v1)   │  │ (Domain → HTTP mapping) │ │
│  └──────────┘  └─────┬──────┘  └─────────────────────────┘ │
│                      │                                      │
│              ┌───────▼───────┐                              │
│              │   Services    │  ← Business logic layer      │
│              │ (transactions,│    Domain exceptions only     │
│              │  validation)  │    Never raises HTTPException │
│              └───────┬───────┘                              │
│                      │                                      │
│              ┌───────▼───────┐                              │
│              │ Repositories  │  ← Data access layer         │
│              │ (queries,     │    Never commits              │
│              │  no commits)  │    Returns ORM models         │
│              └───────┬───────┘                              │
│                      │                                      │
│              ┌───────▼───────┐                              │
│              │  SQLAlchemy   │  ← ORM models                │
│              │  (Mapped,     │    DeclarativeBase            │
│              │  mapped_col)  │    Type-hinted columns        │
│              └───────┬───────┘                              │
│                      │                                      │
│              ┌───────▼───────┐                              │
│              │    SQLite     │  ← WAL mode, FK enforcement  │
│              └───────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**

- **Sync SQLAlchemy** — SQLite doesn't benefit from async; sync is simpler and avoids greenlet overhead.
- **Repository Pattern** — Repositories handle queries but never commit; services manage transaction boundaries.
- **Domain Exceptions** — Services raise typed domain exceptions (`NotFoundError`, `ConflictError`, etc.), never `HTTPException`. Exception handlers translate these to HTTP responses.
- **Bug Injection** — Configurable flags in `.env` activate deliberate bugs for QA testing.

---

## 📁 Project Structure

```
.
├── alembic/                    # Database migration scripts
│   ├── env.py                  # Migration environment config
│   ├── script.py.mako          # Migration template
│   └── versions/               # Generated migration files
├── app/
│   ├── api/
│   │   ├── deps.py             # Shared FastAPI dependencies
│   │   └── v1/                 # Versioned API routes
│   │       ├── auth.py         # Register, login, refresh, /me
│   │       ├── customers.py    # Customer CRUD
│   │       ├── products.py     # Product catalogue CRUD
│   │       ├── inventory.py    # Warehouse inventory management
│   │       ├── orders.py       # Order lifecycle management
│   │       ├── payments.py     # Payment processing & refunds
│   │       ├── shipments.py    # Shipment tracking
│   │       ├── coupons.py      # Discount coupon management
│   │       ├── reports.py      # Analytics & reporting
│   │       ├── audit_logs.py   # Immutable audit trail
│   │       └── router.py       # Aggregated v1 router
│   ├── auth/
│   │   ├── jwt.py              # PyJWT token create/decode
│   │   ├── passwords.py        # bcrypt hash/verify
│   │   └── permissions.py      # Role-based access checker
│   ├── bugs/
│   │   ├── injectors.py        # Bug injection implementations
│   │   └── registry.py         # Bug flag lookup registry
│   ├── core/
│   │   ├── config.py           # Pydantic Settings
│   │   └── enums.py            # Domain enumerations
│   ├── database/
│   │   ├── base.py             # DeclarativeBase
│   │   └── session.py          # Engine, SessionLocal, get_db
│   ├── exceptions/
│   │   ├── base.py             # Domain exception hierarchy
│   │   └── handlers.py         # Exception → HTTP response mapping
│   ├── logging/
│   │   └── setup.py            # Loguru configuration
│   ├── middleware/
│   │   └── logging.py          # Request/response logging
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py, customer.py, product.py, inventory.py
│   │   ├── order.py, payment.py, shipment.py, coupon.py
│   │   └── audit_log.py
│   ├── repositories/           # Data access layer
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic layer
│   └── main.py                 # App factory & startup
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures
│   ├── test_health.py          # Health & docs tests
│   ├── test_auth.py            # Authentication tests
│   └── test_customers.py       # Customer CRUD tests
├── .env.example                # Environment template
├── .gitignore                  # Git exclusions
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Python dependencies
└── README.md                   # ← You are here
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or a virtual environment manager

### 1. Clone and set up

```bash
# Clone the repository
git clone <repo-url>
cd "backend testing application"

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest httpx
```

### 2. Configure environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env if needed (defaults work for local development)
```

### 3. Start the server

```bash
# Option A: Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option B: Using Python
python -m uvicorn app.main:app --reload
```

### 4. Explore the API

Open your browser:

| URL                              | Description          |
|----------------------------------|----------------------|
| http://localhost:8000/docs       | Swagger UI (interactive) |
| http://localhost:8000/redoc      | ReDoc (readable)     |
| http://localhost:8000/health     | Health check         |
| http://localhost:8000/openapi.json | Raw OpenAPI schema |

---

## ⚙ Environment Variables

All variables are configured in `.env`. Defaults are suitable for development.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment: `development`, `staging`, `production` |
| `APP_HOST` | `0.0.0.0` | Server bind host |
| `APP_PORT` | `8000` | Server bind port |
| `APP_DEBUG` | `true` | Enable debug mode (SQL echo, verbose errors) |
| `APP_TITLE` | `Order Management System` | OpenAPI title |
| `APP_VERSION` | `1.0.0` | OpenAPI version |
| `DATABASE_URL` | `sqlite:///./oms.db` | SQLAlchemy connection string |
| `JWT_SECRET_KEY` | `change-this-...` | **Change in production!** JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format: `json` or `human` |
| `ENABLE_NEGATIVE_INVENTORY` | `false` | 🐛 Allow stock to go negative |
| `ENABLE_DUPLICATE_PAYMENT` | `false` | 🐛 Skip duplicate transaction check |
| `ENABLE_WRONG_GST` | `false` | 🐛 Apply incorrect GST calculation |
| `ENABLE_SKIP_AUDIT_LOG` | `false` | 🐛 Silently drop audit entries |
| `ENABLE_SHIPMENT_WITHOUT_PAYMENT` | `false` | 🐛 Allow shipping unpaid orders |

---

## 🔐 Authentication Guide

The API uses **JWT Bearer token** authentication with role-based access control.

### Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full access to all resources and operations |
| **manager** | CRUD on business entities, reports (no user management) |
| **user** | Read access + create orders + process payments |

### Step 1: Register a user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "secret123"}'
```

### Step 2: Login to get tokens

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=john&password=secret123"
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Step 3: Use the token

```bash
# Include the token in the Authorization header
curl http://localhost:8000/api/v1/customers/ \
  -H "Authorization: Bearer eyJ..."
```

### Step 4: Refresh an expired token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

> **💡 Tip:** In Swagger UI (`/docs`), click the **Authorize** 🔒 button and enter your username/password. Swagger will handle the OAuth2 flow automatically.

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|:---:|
| POST | `/api/v1/auth/register` | Register a new user | ❌ |
| POST | `/api/v1/auth/login` | Login (returns JWT tokens) | ❌ |
| POST | `/api/v1/auth/refresh` | Refresh access token | ❌ |
| GET | `/api/v1/auth/me` | Get current user profile | ✅ |

### Customers

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/customers/` | Create customer | Admin, Manager |
| GET | `/api/v1/customers/` | List customers (paginated) | All |
| GET | `/api/v1/customers/{id}` | Get customer by ID | All |
| PUT | `/api/v1/customers/{id}` | Update customer | Admin, Manager |
| DELETE | `/api/v1/customers/{id}` | Delete customer | Admin |

### Products

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/products/` | Create product | Admin, Manager |
| GET | `/api/v1/products/` | List products (paginated) | All |
| GET | `/api/v1/products/{id}` | Get product by ID | All |
| PUT | `/api/v1/products/{id}` | Update product | Admin, Manager |
| DELETE | `/api/v1/products/{id}` | Delete product | Admin |

### Inventory

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/inventory/` | Create inventory record | Admin, Manager |
| GET | `/api/v1/inventory/` | List inventory (paginated) | All |
| GET | `/api/v1/inventory/{id}` | Get inventory record | All |
| PUT | `/api/v1/inventory/{id}` | Update stock levels | Admin, Manager |

### Orders

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/orders/` | Create order | All |
| GET | `/api/v1/orders/` | List orders (paginated) | All |
| GET | `/api/v1/orders/{id}` | Get order by ID | All |
| PUT | `/api/v1/orders/{id}/status` | Update order status | Admin, Manager |
| DELETE | `/api/v1/orders/{id}` | Cancel order | All |

### Payments

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/payments/` | Process payment | All |
| GET | `/api/v1/payments/` | List payments | All |
| GET | `/api/v1/payments/{id}` | Get payment by ID | All |
| POST | `/api/v1/payments/{id}/refund` | Refund payment | Admin, Manager |

### Shipments

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/shipments/` | Create shipment | Admin, Manager |
| GET | `/api/v1/shipments/` | List shipments | All |
| GET | `/api/v1/shipments/{id}` | Get shipment by ID | All |
| PUT | `/api/v1/shipments/{id}/status` | Update shipment status | Admin, Manager |

### Coupons

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v1/coupons/` | Create coupon | Admin |
| GET | `/api/v1/coupons/` | List coupons (paginated) | All |
| GET | `/api/v1/coupons/{code}` | Get coupon by code | All |
| PUT | `/api/v1/coupons/{code}` | Update coupon | Admin |
| DELETE | `/api/v1/coupons/{code}` | Deactivate coupon | Admin |

### Reports

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/v1/reports/sales` | Sales analytics | Admin, Manager |
| GET | `/api/v1/reports/orders` | Order statistics | Admin, Manager |
| GET | `/api/v1/reports/inventory` | Inventory summary | Admin, Manager |
| GET | `/api/v1/reports/customers` | Customer analytics | Admin, Manager |

### Audit Logs

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/v1/audit-logs/` | Query audit trail | Admin |

---

## 🐛 Bug Injection Guide

The OMS includes **5 deliberately injectable bugs** for testing and QA training. Enable them by setting the corresponding environment variable to `true` in `.env`.

### 1. Negative Inventory (`ENABLE_NEGATIVE_INVENTORY`)

**What it does:** Skips the stock availability check, allowing inventory quantities to go below zero.

**How to detect:**
- Create an order with a quantity exceeding available stock
- Check that inventory has a negative `quantity` value
- Verify this shouldn't be allowed by business rules

### 2. Duplicate Payment (`ENABLE_DUPLICATE_PAYMENT`)

**What it does:** Bypasses the duplicate transaction ID check, allowing the same payment to be recorded multiple times.

**How to detect:**
- Submit the same payment twice with the same transaction reference
- Verify that only one payment should exist per transaction

### 3. Wrong GST Calculation (`ENABLE_WRONG_GST`)

**What it does:** Applies an incorrect GST rate (e.g., wrong percentage or formula).

**How to detect:**
- Create an order and verify the `gst_amount` and `total_amount`
- Calculate expected GST manually and compare
- The difference indicates the bug is active

### 4. Skip Audit Log (`ENABLE_SKIP_AUDIT_LOG`)

**What it does:** Silently drops audit log entries — operations succeed but leave no audit trail.

**How to detect:**
- Perform CRUD operations (create, update, delete)
- Query `/api/v1/audit-logs/` and verify entries are missing
- All state-changing operations should have an audit record

### 5. Shipment Without Payment (`ENABLE_SHIPMENT_WITHOUT_PAYMENT`)

**What it does:** Allows creating a shipment for an order that hasn't been paid.

**How to detect:**
- Create an order (status: `pending`)
- Attempt to create a shipment without processing payment
- Verify that shipments should only be created for paid orders

### Activating Bugs

```bash
# In .env file:
ENABLE_NEGATIVE_INVENTORY=true
ENABLE_DUPLICATE_PAYMENT=true
ENABLE_WRONG_GST=true
ENABLE_SKIP_AUDIT_LOG=true
ENABLE_SHIPMENT_WITHOUT_PAYMENT=true
```

> **⚠️ Warning:** Restart the server after changing `.env` values for them to take effect.

---

## 🧪 Testing Guide

### Prerequisites

```bash
pip install pytest httpx
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py

# Run a specific test
pytest tests/test_auth.py::test_login -v

# Run with coverage (requires pytest-cov)
pip install pytest-cov
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Test Architecture

- **In-memory SQLite** — Each test gets a fresh database (created and dropped per test function).
- **Dependency Override** — `get_db` is overridden to use the test session; no real database is touched.
- **Fixture Hierarchy** — `db_session` → `client` → `admin_user` → `admin_token` → `auth_headers`.

### Test Files

| File | Coverage |
|------|----------|
| `tests/test_health.py` | Health check, docs availability, OpenAPI schema |
| `tests/test_auth.py` | Registration, login, refresh, /me, token validation |
| `tests/test_customers.py` | Full CRUD, pagination, duplicates, role enforcement |

### Writing New Tests

```python
# tests/test_products.py
def test_create_product(client, auth_headers):
    response = client.post("/api/v1/products/", json={
        "name": "Widget",
        "sku": "WDG-001",
        "price": 29.99,
        "gst_rate": 18.0,
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["sku"] == "WDG-001"
```

---

## 📄 License

This project is for educational and QA testing purposes.
