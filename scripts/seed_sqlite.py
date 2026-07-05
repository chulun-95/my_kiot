#!/usr/bin/env python3
"""
Seed dữ liệu test vào SQLite dev.db (database mà app mobile đang dùng).

Tạo:
  • 1 tenant + 2 users (owner + cashier)
  • Các danh mục cần thiết (2 cấp)
  • 10 nhà cung cấp (2 có công nợ)
  • 100 sản phẩm
  • 30 khách hàng
  • Tồn kho đầu kỳ cho mọi sản phẩm + kardex (stock_movements) nhất quán

Chạy:  .venv\\Scripts\\python.exe scripts/seed_sqlite.py
Mặc định seed vào ./dev.db ; có thể override bằng env DATABASE_URL.

Login sau khi seed:
  OWNER   : 0901234567 / owner123
  CASHIER : 0912345678 / cashier123
"""
from __future__ import annotations

import asyncio
import os
import random
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import bcrypt
from sqlalchemy import delete, event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.shared.text import vi_unaccent
from backend.shared.models import Base

# Import data lists từ seed_demo (Postgres seeder) để khỏi lặp lại 100 dòng sản phẩm
from scripts.seed_demo import CATEGORIES, SUPPLIERS, PRODUCTS_DATA, CUSTOMERS

# Models
from backend.modules.tenant.models import Tenant
from backend.modules.auth.models import User, RefreshToken
from backend.modules.product.models import Category, Product, ProductImage, ProductUnit
from backend.modules.customer.models import Customer, Supplier
from backend.modules.inventory.models import (
    GoodsReceipt, GoodsReceiptItem, Inventory, StockMovement,
)
from backend.modules.sales.models import Invoice, InvoiceItem, Payment, ReturnOrder, ReturnOrderItem
from backend.modules.cashbook.models import CashTransaction
from backend.modules.system.models import AuditLog, PriceHistory
from backend.shared.code_generator import CodeSequence

random.seed(42)
TZ = timezone.utc
TENANT_SLUG = "tap-hoa-my-linh"
N_SUPPLIERS = 10  # chỉ lấy 10 NCC theo yêu cầu

DB_URL = os.environ.get("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'dev.db'}")


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=4)).decode()


def D(v) -> Decimal:
    return Decimal(str(v))


async def main() -> None:
    engine = create_async_engine(DB_URL)

    @event.listens_for(engine.sync_engine, "connect")
    def _register_funcs(dbapi_conn, _):
        try:
            dbapi_conn.create_function("immutable_unaccent", 1, vi_unaccent)
        except Exception:
            pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(TZ)

    async with Session() as db:
        # ── Reset tenant cũ nếu có ────────────────────────────────────────
        existing = (await db.execute(
            select(Tenant).where(Tenant.slug == TENANT_SLUG)
        )).scalar_one_or_none()
        if existing:
            tid = existing.id
            print(f"Tenant '{TENANT_SLUG}' đã tồn tại (id={tid}) → xóa và tạo lại...")
            user_ids = (await db.execute(
                select(User.id).where(User.tenant_id == tid)
            )).scalars().all()
            if user_ids:
                await db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids)))
            for model in (
                StockMovement, Inventory, GoodsReceiptItem, GoodsReceipt,
                InvoiceItem, Payment, ReturnOrderItem, ReturnOrder, Invoice,
                CashTransaction, PriceHistory, AuditLog,
                ProductUnit, ProductImage, Product, Category,
                Customer, Supplier, CodeSequence, User,
            ):
                col = getattr(model, "tenant_id", None)
                if col is not None:
                    await db.execute(delete(model).where(col == tid))
            await db.execute(delete(Tenant).where(Tenant.id == tid))
            await db.commit()

        # ── 1. Tenant ─────────────────────────────────────────────────────
        tenant = Tenant(
            name="Tạp Hóa Mỹ Linh", slug=TENANT_SLUG, phone="0901234567",
            email="mylinh@taphoamylinh.vn",
            address="123 Nguyễn Văn Lương, Phường 10, Quận 6, TP.HCM",
            settings={
                "allow_debt": True,
                "default_payment_method": "CASH",
                "low_stock_threshold_default": 5,
                "show_cost_to_cashier": False,
            },
            is_active=True, created_at=now, updated_at=now,
        )
        db.add(tenant)
        await db.flush()
        print(f"✓ Tenant id={tenant.id}")

        # ── 2. Users ──────────────────────────────────────────────────────
        owner = User(
            tenant_id=tenant.id, phone="0901234567", email="mylinh@taphoamylinh.vn",
            full_name="Nguyễn Thị Mỹ Linh", password_hash=_hash("owner123"),
            role="OWNER", is_active=True, created_at=now, updated_at=now,
        )
        cashier = User(
            tenant_id=tenant.id, phone="0912345678", email=None,
            full_name="Trần Văn Nam", password_hash=_hash("cashier123"),
            role="CASHIER", is_active=True, created_at=now, updated_at=now,
        )
        db.add_all([owner, cashier])
        await db.flush()
        print(f"✓ Users: owner={owner.id}, cashier={cashier.id}")

        # ── 3. Categories ─────────────────────────────────────────────────
        cat_id: dict[str, int] = {}
        for key, name, depth, parent_key in CATEGORIES:
            cat = Category(
                tenant_id=tenant.id,
                parent_id=cat_id.get(parent_key) if parent_key else None,
                name=name, depth=depth, sort_order=0,
                created_at=now, updated_at=now,
            )
            db.add(cat)
            await db.flush()
            cat_id[key] = cat.id
        print(f"✓ Categories: {len(cat_id)}")

        # ── 4. Suppliers (10) ─────────────────────────────────────────────
        sup_ids: list[int] = []
        for key, name, phone, addr, tax, has_debt in SUPPLIERS[:N_SUPPLIERS]:
            sup = Supplier(
                tenant_id=tenant.id, name=name, phone=phone, address=addr,
                tax_code=tax,
                total_debt=D(random.choice([1_500_000, 3_200_000])) if has_debt else D(0),
                created_at=now, updated_at=now,
            )
            db.add(sup)
            await db.flush()
            sup_ids.append(sup.id)
        print(f"✓ Suppliers: {len(sup_ids)}")

        # ── 5. Products (100) + tồn kho + kardex ──────────────────────────
        n_prod = 0
        for i, (name, cat_key, unit, cost, sale, barcode, min_stock, _sup, _monthly) in enumerate(PRODUCTS_DATA[:100]):
            prod = Product(
                tenant_id=tenant.id, category_id=cat_id.get(cat_key),
                sku=f"SP{i+1:04d}", barcode=barcode, name=name, unit=unit,
                cost_price=D(cost), sale_price=D(sale), min_stock=min_stock,
                status="ACTIVE", allow_negative=False,
                created_by=owner.id, created_at=now, updated_at=now,
            )
            db.add(prod)
            await db.flush()

            # Tồn đầu kỳ ngẫu nhiên
            qty = D(random.randint(20, 200))
            db.add(Inventory(
                tenant_id=tenant.id, product_id=prod.id, quantity=qty, updated_at=now,
            ))
            db.add(StockMovement(
                tenant_id=tenant.id, product_id=prod.id, quantity=qty,
                unit_cost=D(cost), type="RECEIPT", ref_type="MANUAL",
                ref_id=owner.id, balance_after=qty, note="Tồn đầu kỳ (seed)",
                created_at=now, created_by=owner.id,
            ))
            n_prod += 1
        print(f"✓ Products: {n_prod} (kèm tồn kho + kardex)")

        # ── 6. Customers ──────────────────────────────────────────────────
        for cname, cphone, caddr in CUSTOMERS:
            db.add(Customer(
                tenant_id=tenant.id, name=cname, phone=cphone, address=caddr,
                total_spent=D(0), total_orders=0, created_at=now, updated_at=now,
            ))
        print(f"✓ Customers: {len(CUSTOMERS)}")

        await db.commit()

    await engine.dispose()

    print("\n" + "─" * 50)
    print("✅ Seed SQLite hoàn tất!")
    print(f"   DB           : {DB_URL}")
    print("   Login OWNER  : 0901234567 / owner123")
    print("   Login CASHIER: 0912345678 / cashier123")
    print("─" * 50)


if __name__ == "__main__":
    asyncio.run(main())
