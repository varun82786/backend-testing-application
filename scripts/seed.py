#!/usr/bin/env python3
"""Database seed script for the Order Management System.

Populates the database with realistic, deterministic test data for
development and testing. Uses random.seed(42) for reproducibility.

Usage:
    python scripts/seed.py

Must be run from the project root directory.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# ── Ensure the project root is on sys.path ────────────────────────
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.orm import sessionmaker

from app.auth.passwords import hash_password
from app.core.enums import (
    AuditAction,
    DiscountType,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ShipmentStatus,
    UserRole,
)
from app.database.base import Base
from app.database.session import engine
from app.models import (
    AuditLog,
    Coupon,
    Customer,
    Inventory,
    Order,
    OrderItem,
    Payment,
    Product,
    Shipment,
    User,
)

# ── Deterministic randomness ──────────────────────────────────────
random.seed(42)

# ── Session factory ───────────────────────────────────────────────
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ── Timestamp helpers ─────────────────────────────────────────────
NOW = datetime(2026, 6, 29, 12, 0, 0)
ONE_DAY = timedelta(days=1)


def _past(max_days: int = 90) -> datetime:
    """Return a random datetime within the last ``max_days`` days."""
    return NOW - timedelta(
        days=random.randint(1, max_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def _recent(max_days: int = 30) -> datetime:
    """Return a random datetime within the last ``max_days`` days."""
    return NOW - timedelta(
        days=random.randint(0, max_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


# =====================================================================
# DATA DEFINITIONS
# =====================================================================

# ── Users ─────────────────────────────────────────────────────────
USERS_DATA = [
    {"username": "admin", "email": "admin@oms.com", "password": "admin123", "role": UserRole.ADMIN},
    {"username": "manager", "email": "manager@oms.com", "password": "manager123", "role": UserRole.MANAGER},
    {"username": "user", "email": "user@oms.com", "password": "user123", "role": UserRole.USER},
]

# ── Customers ─────────────────────────────────────────────────────
INDIAN_NAMES = [
    "Aarav Sharma", "Priya Patel", "Rohan Gupta", "Ananya Singh",
    "Vikram Reddy", "Sneha Iyer", "Arjun Nair", "Kavya Menon",
    "Raj Malhotra", "Deepika Joshi", "Amit Deshmukh", "Pooja Kulkarni",
    "Karthik Raman", "Meera Bhat", "Siddharth Rao", "Neha Verma",
    "Aditya Chopra", "Riya Agarwal", "Manish Tiwari", "Divya Kapoor",
]

INDIAN_CITIES = [
    ("Mumbai", "Maharashtra", "400001"),
    ("Delhi", "Delhi", "110001"),
    ("Bangalore", "Karnataka", "560001"),
    ("Chennai", "Tamil Nadu", "600001"),
    ("Kolkata", "West Bengal", "700001"),
    ("Hyderabad", "Telangana", "500001"),
    ("Pune", "Maharashtra", "411001"),
    ("Ahmedabad", "Gujarat", "380001"),
    ("Jaipur", "Rajasthan", "302001"),
    ("Lucknow", "Uttar Pradesh", "226001"),
]

STREETS = [
    "MG Road", "Park Street", "Brigade Road", "Linking Road",
    "Anna Salai", "FC Road", "Banjara Hills", "Salt Lake",
    "Connaught Place", "Residency Road", "Commercial Street",
    "Carter Road", "Infantry Road", "Boat Club Road", "Juhu Lane",
    "Raja Park", "Lajpat Nagar", "Karol Bagh", "Koramangala",
    "Indiranagar",
]

# ── Products ──────────────────────────────────────────────────────
PRODUCTS_DATA: list[dict] = []

# Electronics (10) — GST 18%
_electronics = [
    ("Dell Inspiron 15 Laptop", "15.6-inch FHD display, Intel i5, 8GB RAM, 512GB SSD", 54999.00),
    ("Samsung Galaxy S24", "6.2-inch AMOLED, Snapdragon 8 Gen 3, 128GB", 79999.00),
    ("Sony WH-1000XM5 Headphones", "Industry-leading noise cancelling, 30hr battery", 24990.00),
    ("Apple iPad Air M2", "11-inch Liquid Retina, M2 chip, 128GB Wi-Fi", 59900.00),
    ("JBL Charge 5 Speaker", "Portable Bluetooth speaker, IP67 waterproof", 12999.00),
    ("Logitech MX Master 3S Mouse", "Ergonomic wireless mouse, 8000 DPI", 8995.00),
    ("Samsung 27\" 4K Monitor", "27-inch UHD IPS panel, USB-C, HDR10", 32999.00),
    ("Apple AirPods Pro 2", "Active noise cancellation, spatial audio, USB-C", 24900.00),
    ("Lenovo Tab P12", "12.7-inch 2K display, Snapdragon 870, 128GB", 29999.00),
    ("Canon EOS R50 Camera", "24.2MP mirrorless, 4K video, dual pixel AF", 74990.00),
]
for i, (name, desc, price) in enumerate(_electronics, 1):
    PRODUCTS_DATA.append({
        "sku": f"ELEC-{i:03d}",
        "name": name,
        "description": desc,
        "price": Decimal(str(price)),
        "gst_percentage": Decimal("18.00"),
        "active": True,
    })

# Clothing (10) — GST 12%
_clothing = [
    ("Raymond Cotton Formal Shirt", "Slim fit, 100% cotton, wrinkle-free", 1899.00),
    ("Levi's 511 Slim Fit Jeans", "Dark wash denim, stretch fit", 2999.00),
    ("Nike Air Max 270 Shoes", "Lightweight running shoes, mesh upper", 4995.00),
    ("Allen Solly Polo T-Shirt", "Classic fit, pique cotton, collar neck", 1299.00),
    ("Van Heusen Blazer", "Single-breasted, polyester blend, formal", 4499.00),
    ("Puma Track Pants", "Dri-fit, elastic waist, zippered pockets", 1799.00),
    ("Woodland Leather Belt", "Genuine leather, pin buckle, brown", 899.00),
    ("Monte Carlo Sweater", "Crew neck, wool blend, winter wear", 1699.00),
    ("Bata Formal Shoes", "Oxford style, faux leather, cushioned sole", 2499.00),
    ("Peter England Chinos", "Regular fit, cotton stretch, flat front", 1599.00),
]
for i, (name, desc, price) in enumerate(_clothing, 1):
    PRODUCTS_DATA.append({
        "sku": f"CLTH-{i:03d}",
        "name": name,
        "description": desc,
        "price": Decimal(str(price)),
        "gst_percentage": Decimal("12.00"),
        "active": True if i <= 8 else False,  # CLTH-009, CLTH-010 inactive
    })

# Books (10) — GST 5%
_books = [
    ("The White Tiger - Aravind Adiga", "Booker Prize winner, darkly humorous tale of India", 350.00),
    ("Wings of Fire - APJ Abdul Kalam", "Autobiography of India's missile man", 299.00),
    ("The God of Small Things", "Arundhati Roy's Booker Prize-winning debut", 399.00),
    ("Train to Pakistan - Khushwant Singh", "Partition-era novel set in a Punjab village", 250.00),
    ("Clean Code - Robert C. Martin", "A handbook of agile software craftsmanship", 1899.00),
    ("Designing Data-Intensive Applications", "Martin Kleppmann's guide to distributed systems", 1999.00),
    ("The Pragmatic Programmer", "From journeyman to master, 20th anniversary edition", 1799.00),
    ("Sapiens - Yuval Noah Harari", "A brief history of humankind", 499.00),
    ("Atomic Habits - James Clear", "Tiny changes, remarkable results", 449.00),
    ("The Alchemist - Paulo Coelho", "A fable about following your dream", 299.00),
]
for i, (name, desc, price) in enumerate(_books, 1):
    PRODUCTS_DATA.append({
        "sku": f"BOOK-{i:03d}",
        "name": name,
        "description": desc,
        "price": Decimal(str(price)),
        "gst_percentage": Decimal("5.00"),
        "active": True,
    })

# Home & Kitchen (10) — GST 18%
_home = [
    ("Prestige Iris 750W Mixer Grinder", "3 jars, stainless steel blades, overload protection", 3499.00),
    ("Philips HD6975 Digital Oven", "25L capacity, 1500W, 10 preset menus", 7999.00),
    ("Hawkins Contura 5L Pressure Cooker", "Hard anodized, induction compatible", 2899.00),
    ("Pigeon Favourite IC 1800W Induction", "Crystal glass top, push button control", 1499.00),
    ("Borosil 1L Glass Carafe", "Borosilicate glass, heat resistant, with lid", 799.00),
    ("Milton Thermosteel Flask 1L", "24-hour hot/cold retention, stainless steel", 699.00),
    ("Butterfly Rapid 1.5L Kettle", "Stainless steel, auto shut-off, 1500W", 899.00),
    ("Wipro 9W LED Bulb Pack of 6", "Cool daylight, B22 base, 10000hr life", 549.00),
    ("Prestige Non-Stick Kadai 24cm", "3-layer coating, induction base, glass lid", 1199.00),
    ("IFB Neptune VX Dishwasher", "12 place settings, 8 wash programs, steam drying", 29990.00),
]
for i, (name, desc, price) in enumerate(_home, 1):
    PRODUCTS_DATA.append({
        "sku": f"HOME-{i:03d}",
        "name": name,
        "description": desc,
        "price": Decimal(str(price)),
        "gst_percentage": Decimal("18.00"),
        "active": True if i <= 9 else False,  # HOME-010 inactive
    })

# Sports (10) — GST 28%
_sports = [
    ("Yonex Nanoray Light 18i Racket", "Isometric head, graphite frame, lightweight", 2490.00),
    ("Nivia Storm Football Size 5", "Rubberized molded, hand stitched", 799.00),
    ("SG RSD Xtreme Cricket Bat", "English willow, full size, short handle", 5999.00),
    ("Fitbit Charge 6 Fitness Tracker", "GPS, heart rate, stress management, 7-day battery", 14999.00),
    ("Cosco 25004 Table Tennis Set", "2 rackets, 3 balls, net set", 1299.00),
    ("Adidas Predator Football Boots", "Firm ground, control skin, lace-up", 8999.00),
    ("Head Tour Team Tennis Bag", "6-racket capacity, padded, shoe compartment", 3999.00),
    ("Kobo 10kg Dumbbell Set", "Cast iron, rubber grip, adjustable plates", 2499.00),
    ("Strauss Yoga Mat 6mm", "Anti-skid, NBR foam, carrying strap", 699.00),
    ("Hero Sprint Howler 26T Cycle", "21-speed, front disc brake, double wall rim", 12999.00),
]
for i, (name, desc, price) in enumerate(_sports, 1):
    PRODUCTS_DATA.append({
        "sku": f"SPRT-{i:03d}",
        "name": name,
        "description": desc,
        "price": Decimal(str(price)),
        "gst_percentage": Decimal("28.00"),
        "active": True,
    })

# ── Warehouses ────────────────────────────────────────────────────
WAREHOUSES = ["WH-MUMBAI", "WH-DELHI", "WH-BANGALORE", "WH-CHENNAI", "WH-KOLKATA"]

# ── Coupons ───────────────────────────────────────────────────────
COUPONS_DATA = [
    # Active percentage coupons
    {
        "code": "SAVE10",
        "discount_type": DiscountType.PERCENTAGE,
        "discount_value": Decimal("10.00"),
        "minimum_order": Decimal("1000.00"),
        "expiry": NOW + timedelta(days=60),
        "active": True,
        "single_use": False,
        "used": False,
    },
    {
        "code": "SAVE20",
        "discount_type": DiscountType.PERCENTAGE,
        "discount_value": Decimal("20.00"),
        "minimum_order": Decimal("5000.00"),
        "expiry": NOW + timedelta(days=30),
        "active": True,
        "single_use": False,
        "used": False,
    },
    {
        "code": "MEGA25",
        "discount_type": DiscountType.PERCENTAGE,
        "discount_value": Decimal("25.00"),
        "minimum_order": Decimal("10000.00"),
        "expiry": NOW + timedelta(days=45),
        "active": True,
        "single_use": False,
        "used": False,
    },
    # Active flat coupons
    {
        "code": "FLAT500",
        "discount_type": DiscountType.FLAT,
        "discount_value": Decimal("500.00"),
        "minimum_order": Decimal("2000.00"),
        "expiry": NOW + timedelta(days=90),
        "active": True,
        "single_use": False,
        "used": False,
    },
    {
        "code": "FLAT1000",
        "discount_type": DiscountType.FLAT,
        "discount_value": Decimal("1000.00"),
        "minimum_order": Decimal("5000.00"),
        "expiry": NOW + timedelta(days=60),
        "active": True,
        "single_use": False,
        "used": False,
    },
    # High minimum order coupon
    {
        "code": "PREMIUM50",
        "discount_type": DiscountType.PERCENTAGE,
        "discount_value": Decimal("50.00"),
        "minimum_order": Decimal("50000.00"),
        "expiry": NOW + timedelta(days=30),
        "active": True,
        "single_use": False,
        "used": False,
    },
    # Expired coupons
    {
        "code": "DIWALI30",
        "discount_type": DiscountType.PERCENTAGE,
        "discount_value": Decimal("30.00"),
        "minimum_order": Decimal("3000.00"),
        "expiry": NOW - timedelta(days=90),
        "active": False,
        "single_use": False,
        "used": False,
    },
    {
        "code": "NEWYEAR500",
        "discount_type": DiscountType.FLAT,
        "discount_value": Decimal("500.00"),
        "minimum_order": Decimal("1500.00"),
        "expiry": NOW - timedelta(days=180),
        "active": False,
        "single_use": False,
        "used": False,
    },
    # Used single-use coupons
    {
        "code": "WELCOME100",
        "discount_type": DiscountType.FLAT,
        "discount_value": Decimal("100.00"),
        "minimum_order": Decimal("500.00"),
        "expiry": NOW + timedelta(days=30),
        "active": True,
        "single_use": True,
        "used": True,
    },
    {
        "code": "FIRSTORDER",
        "discount_type": DiscountType.PERCENTAGE,
        "discount_value": Decimal("15.00"),
        "minimum_order": Decimal("1000.00"),
        "expiry": NOW + timedelta(days=60),
        "active": True,
        "single_use": True,
        "used": True,
    },
]

# ── Carriers ──────────────────────────────────────────────────────
CARRIERS = ["FedEx", "DHL", "BlueDart", "DTDC", "India Post"]

# ── Payment methods ───────────────────────────────────────────────
PAYMENT_METHODS = [
    PaymentMethod.CREDIT_CARD,
    PaymentMethod.DEBIT_CARD,
    PaymentMethod.UPI,
    PaymentMethod.NET_BANKING,
    PaymentMethod.WALLET,
    PaymentMethod.CASH_ON_DELIVERY,
]


# =====================================================================
# SEED FUNCTIONS
# =====================================================================


def seed_users(session) -> list[User]:
    """Seed the users table with 3 predefined users."""
    print("  → Seeding users...", end=" ")
    users = []
    for data in USERS_DATA:
        user = User(
            username=data["username"],
            email=data["email"],
            hashed_password=hash_password(data["password"]),
            role=data["role"],
            is_active=True,
        )
        session.add(user)
        users.append(user)
    session.flush()
    print(f"✓ {len(users)} users")
    return users


def seed_customers(session) -> list[Customer]:
    """Seed the customers table with 20 realistic Indian customers."""
    print("  → Seeding customers...", end=" ")
    customers = []
    for i, name in enumerate(INDIAN_NAMES):
        first_name = name.split()[0].lower()
        last_name = name.split()[1].lower()
        city, state, pin = INDIAN_CITIES[i % len(INDIAN_CITIES)]
        street = STREETS[i % len(STREETS)]
        house_no = random.randint(1, 500)

        customer = Customer(
            name=name,
            email=f"{first_name}.{last_name}@email.com",
            phone=f"+91{random.randint(7000000000, 9999999999)}",
            address=f"{house_no}, {street}, {city}, {state} - {pin}",
            loyalty_points=random.choice([0, 0, 100, 250, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 5000]),
        )
        session.add(customer)
        customers.append(customer)
    session.flush()
    print(f"✓ {len(customers)} customers")
    return customers


def seed_products(session) -> list[Product]:
    """Seed the products table with 50 products across 5 categories."""
    print("  → Seeding products...", end=" ")
    products = []
    for data in PRODUCTS_DATA:
        product = Product(
            sku=data["sku"],
            name=data["name"],
            description=data["description"],
            price=data["price"],
            gst_percentage=data["gst_percentage"],
            active=data["active"],
        )
        session.add(product)
        products.append(product)
    session.flush()
    print(f"✓ {len(products)} products ({sum(1 for p in products if not p.active)} inactive)")
    return products


def seed_inventory(session, products: list[Product]) -> list[Inventory]:
    """Seed inventory records — distribute products across warehouses.

    Each product appears in 2-4 warehouses with varying stock levels.
    A few entries have intentionally low stock or reserved quantities.
    """
    print("  → Seeding inventory...", end=" ")
    inventory_records = []
    low_stock_count = 0

    for product in products:
        # Each product goes into 2-4 random warehouses
        num_warehouses = random.randint(2, 4)
        selected_warehouses = random.sample(WAREHOUSES, num_warehouses)

        for warehouse in selected_warehouses:
            # ~10% chance of low stock
            if random.random() < 0.10:
                quantity = random.randint(1, 9)
                low_stock_count += 1
            else:
                quantity = random.randint(10, 500)

            # ~15% chance of having reserved quantity
            reserved = 0
            if random.random() < 0.15 and quantity > 5:
                reserved = random.randint(1, min(quantity // 2, 20))

            inv = Inventory(
                product_id=product.id,
                warehouse=warehouse,
                quantity=quantity,
                reserved_quantity=reserved,
            )
            session.add(inv)
            inventory_records.append(inv)

    session.flush()
    print(f"✓ {len(inventory_records)} records ({low_stock_count} low-stock)")
    return inventory_records


def seed_coupons(session) -> list[Coupon]:
    """Seed the coupons table with 10 coupons of various types."""
    print("  → Seeding coupons...", end=" ")
    coupons = []
    for data in COUPONS_DATA:
        coupon = Coupon(
            code=data["code"],
            discount_type=data["discount_type"],
            discount_value=data["discount_value"],
            minimum_order=data["minimum_order"],
            expiry=data["expiry"],
            active=data["active"],
            single_use=data["single_use"],
            used=data["used"],
        )
        session.add(coupon)
        coupons.append(coupon)
    session.flush()
    print(f"✓ {len(coupons)} coupons")
    return coupons


def _calculate_discount(
    subtotal: Decimal,
    coupon: Coupon | None,
) -> Decimal:
    """Calculate discount amount for a coupon applied to an order subtotal."""
    if coupon is None:
        return Decimal("0.00")
    if coupon.discount_type == DiscountType.PERCENTAGE:
        return (subtotal * coupon.discount_value / Decimal("100")).quantize(Decimal("0.01"))
    else:  # FLAT
        return min(coupon.discount_value, subtotal)


def seed_orders(
    session,
    customers: list[Customer],
    products: list[Product],
    coupons: list[Coupon],
) -> tuple[list[Order], list[OrderItem]]:
    """Seed 100 orders across all lifecycle statuses with realistic items.

    Returns:
        Tuple of (orders, all_order_items).
    """
    print("  → Seeding orders...", end=" ")

    active_products = [p for p in products if p.active]
    # Only use active, non-expired, non-used coupons for applying
    usable_coupons = [
        c for c in coupons
        if c.active and not c.used and c.expiry > NOW
    ]

    # Define order distribution by status
    status_distribution = [
        (OrderStatus.PENDING, 20),
        (OrderStatus.PAID, 20),
        (OrderStatus.PACKED, 15),
        (OrderStatus.SHIPPED, 20),
        (OrderStatus.DELIVERED, 15),
        (OrderStatus.CANCELLED, 10),
    ]

    all_orders: list[Order] = []
    all_items: list[OrderItem] = []
    order_index = 0

    for status, count in status_distribution:
        for _ in range(count):
            order_index += 1
            customer = random.choice(customers)

            # Pick 1-5 random active products for this order
            num_items = random.randint(1, 5)
            selected_products = random.sample(
                active_products, min(num_items, len(active_products))
            )

            # Build order items and calculate subtotal + tax
            subtotal = Decimal("0.00")
            tax = Decimal("0.00")
            items_to_add = []

            for prod in selected_products:
                qty = random.randint(1, 3)
                unit_price = prod.price
                total_price = (unit_price * qty).quantize(Decimal("0.01"))
                item_tax = (total_price * prod.gst_percentage / Decimal("100")).quantize(Decimal("0.01"))

                subtotal += total_price
                tax += item_tax

                items_to_add.append({
                    "product_id": prod.id,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_price": total_price,
                })

            # ~30% of orders get a coupon
            coupon_code = None
            applied_coupon = None
            if random.random() < 0.30 and usable_coupons:
                candidate = random.choice(usable_coupons)
                if subtotal >= candidate.minimum_order:
                    applied_coupon = candidate
                    coupon_code = candidate.code

            discount = _calculate_discount(subtotal, applied_coupon)
            total = (subtotal + tax - discount).quantize(Decimal("0.01"))
            if total < Decimal("0.00"):
                total = Decimal("0.00")

            # Create order with a past timestamp
            created_at = _past(max_days=60)

            order = Order(
                customer_id=customer.id,
                status=status,
                subtotal=subtotal,
                tax=tax,
                discount=discount,
                total=total,
                coupon_code=coupon_code,
            )
            session.add(order)
            session.flush()  # Get order.id

            for item_data in items_to_add:
                oi = OrderItem(
                    order_id=order.id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    total_price=item_data["total_price"],
                )
                session.add(oi)
                all_items.append(oi)

            all_orders.append(order)

    session.flush()
    status_counts = {}
    for o in all_orders:
        status_counts[o.status.value] = status_counts.get(o.status.value, 0) + 1
    status_str = ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))
    print(f"✓ {len(all_orders)} orders ({status_str}), {len(all_items)} items")
    return all_orders, all_items


def seed_payments(session, orders: list[Order]) -> list[Payment]:
    """Seed payments for orders that have been paid or beyond.

    Creates payments for: PAID, PACKED, SHIPPED, DELIVERED orders.
    """
    print("  → Seeding payments...", end=" ")
    paid_statuses = {OrderStatus.PAID, OrderStatus.PACKED, OrderStatus.SHIPPED, OrderStatus.DELIVERED}
    payable_orders = [o for o in orders if o.status in paid_statuses]

    payments = []
    for i, order in enumerate(payable_orders, 1):
        payment = Payment(
            order_id=order.id,
            status=PaymentStatus.SUCCESS,
            method=random.choice(PAYMENT_METHODS),
            transaction_reference=f"TXN-{i:04d}",
            amount=order.total,
        )
        session.add(payment)
        payments.append(payment)

    session.flush()
    print(f"✓ {len(payments)} payments")
    return payments


def seed_shipments(session, orders: list[Order]) -> list[Shipment]:
    """Seed shipments for SHIPPED and DELIVERED orders.

    - SHIPPED orders get shipped_at set, status=SHIPPED
    - DELIVERED orders get both shipped_at and delivered_at, status=DELIVERED
    """
    print("  → Seeding shipments...", end=" ")
    shippable_orders = [o for o in orders if o.status in {OrderStatus.SHIPPED, OrderStatus.DELIVERED}]

    shipments = []
    for i, order in enumerate(shippable_orders, 1):
        carrier = random.choice(CARRIERS)
        carrier_prefix = carrier.upper().replace(" ", "")[:3]
        tracking_number = f"{carrier_prefix}{random.randint(100000000, 999999999)}"

        shipped_at = _recent(max_days=20)

        if order.status == OrderStatus.DELIVERED:
            delivered_at = shipped_at + timedelta(days=random.randint(1, 7))
            shipment_status = ShipmentStatus.DELIVERED
        else:
            delivered_at = None
            shipment_status = ShipmentStatus.SHIPPED

        shipment = Shipment(
            order_id=order.id,
            tracking_number=tracking_number,
            carrier=carrier,
            status=shipment_status,
            shipped_at=shipped_at,
            delivered_at=delivered_at,
        )
        session.add(shipment)
        shipments.append(shipment)

    session.flush()
    shipped_count = sum(1 for s in shipments if s.status == ShipmentStatus.SHIPPED)
    delivered_count = sum(1 for s in shipments if s.status == ShipmentStatus.DELIVERED)
    print(f"✓ {len(shipments)} shipments (shipped={shipped_count}, delivered={delivered_count})")
    return shipments


def seed_audit_logs(
    session,
    users: list[User],
    orders: list[Order],
    payments: list[Payment],
) -> list[AuditLog]:
    """Seed audit log entries for key operations.

    Covers: user registrations, order creations, payment processing,
    and order status changes.
    """
    print("  → Seeding audit logs...", end=" ")
    logs = []

    # User registration logs
    for user in users:
        log = AuditLog(
            entity="User",
            entity_id=str(user.id),
            action=AuditAction.REGISTER,
            old_value=None,
            new_value=json.dumps({"username": user.username, "email": user.email, "role": user.role.value}),
            performed_by="system",
        )
        session.add(log)
        logs.append(log)

    # Order creation logs (for all orders)
    for order in orders:
        log = AuditLog(
            entity="Order",
            entity_id=str(order.id),
            action=AuditAction.CREATED,
            old_value=None,
            new_value=json.dumps({
                "customer_id": order.customer_id,
                "status": order.status.value,
                "total": str(order.total),
            }),
            performed_by=random.choice(["admin", "manager", "user", "system"]),
        )
        session.add(log)
        logs.append(log)

    # Payment processing logs
    for payment in payments:
        log = AuditLog(
            entity="Payment",
            entity_id=str(payment.id),
            action=AuditAction.PAYMENT_PROCESSED,
            old_value=json.dumps({"status": PaymentStatus.PENDING.value}),
            new_value=json.dumps({
                "status": PaymentStatus.SUCCESS.value,
                "method": payment.method.value,
                "amount": str(payment.amount),
                "transaction_reference": payment.transaction_reference,
            }),
            performed_by=random.choice(["admin", "manager", "system"]),
        )
        session.add(log)
        logs.append(log)

    # Status change logs for non-pending orders
    for order in orders:
        if order.status == OrderStatus.PENDING:
            continue

        # Simulate the status progression
        transitions = {
            OrderStatus.PAID: [(OrderStatus.PENDING, OrderStatus.PAID)],
            OrderStatus.PACKED: [
                (OrderStatus.PENDING, OrderStatus.PAID),
                (OrderStatus.PAID, OrderStatus.PACKED),
            ],
            OrderStatus.SHIPPED: [
                (OrderStatus.PENDING, OrderStatus.PAID),
                (OrderStatus.PAID, OrderStatus.PACKED),
                (OrderStatus.PACKED, OrderStatus.SHIPPED),
            ],
            OrderStatus.DELIVERED: [
                (OrderStatus.PENDING, OrderStatus.PAID),
                (OrderStatus.PAID, OrderStatus.PACKED),
                (OrderStatus.PACKED, OrderStatus.SHIPPED),
                (OrderStatus.SHIPPED, OrderStatus.DELIVERED),
            ],
            OrderStatus.CANCELLED: [(OrderStatus.PENDING, OrderStatus.CANCELLED)],
        }

        for from_status, to_status in transitions.get(order.status, []):
            log = AuditLog(
                entity="Order",
                entity_id=str(order.id),
                action=AuditAction.STATUS_CHANGED,
                old_value=json.dumps({"status": from_status.value}),
                new_value=json.dumps({"status": to_status.value}),
                performed_by=random.choice(["admin", "manager", "system"]),
            )
            session.add(log)
            logs.append(log)

    session.flush()
    print(f"✓ {len(logs)} audit log entries")
    return logs


# =====================================================================
# MAIN
# =====================================================================


def main() -> None:
    """Run the full database seed process."""
    print("=" * 60)
    print("  Order Management System — Database Seeder")
    print("=" * 60)
    print()

    # ── Drop and recreate all tables ──────────────────────────────
    print("[1/9] Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("  ✓ All tables dropped")

    print("[2/9] Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("  ✓ All tables created")
    print()

    # ── Seed data ─────────────────────────────────────────────────
    session = SessionLocal()
    try:
        print("[3/9] Users")
        users = seed_users(session)

        print("[4/9] Customers")
        customers = seed_customers(session)

        print("[5/9] Products")
        products = seed_products(session)

        print("[6/9] Inventory")
        inventory = seed_inventory(session, products)

        print("[7/9] Coupons")
        coupons = seed_coupons(session)

        print("[8/9] Orders & Order Items")
        orders, order_items = seed_orders(session, customers, products, coupons)

        # Payments — for PAID, PACKED, SHIPPED, DELIVERED orders
        payments = seed_payments(session, orders)

        # Shipments — for SHIPPED, DELIVERED orders
        shipments = seed_shipments(session, orders)

        print("[9/9] Audit Logs")
        audit_logs = seed_audit_logs(session, users, orders, payments)

        # ── Commit everything ─────────────────────────────────────
        session.commit()
        print()
        print("✓ All data committed successfully!")

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error during seeding: {e}")
        raise
    finally:
        session.close()

    # ── Summary ───────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  SEED SUMMARY")
    print("=" * 60)
    print(f"  Users:        {len(users):>6}")
    print(f"  Customers:    {len(customers):>6}")
    print(f"  Products:     {len(products):>6}")
    print(f"  Inventory:    {len(inventory):>6}")
    print(f"  Coupons:      {len(coupons):>6}")
    print(f"  Orders:       {len(orders):>6}")
    print(f"  Order Items:  {len(order_items):>6}")
    print(f"  Payments:     {len(payments):>6}")
    print(f"  Shipments:    {len(shipments):>6}")
    print(f"  Audit Logs:   {len(audit_logs):>6}")
    print(f"  {'─' * 24}")
    total = (
        len(users) + len(customers) + len(products) + len(inventory)
        + len(coupons) + len(orders) + len(order_items) + len(payments)
        + len(shipments) + len(audit_logs)
    )
    print(f"  Total rows:   {total:>6}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
