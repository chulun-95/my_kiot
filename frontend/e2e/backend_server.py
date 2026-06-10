"""
Start backend with SQLite for Playwright E2E tests.
Called by playwright.config.ts webServer.
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # frontend/e2e -> frontend -> project root
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "e2e_test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")
os.environ.setdefault("JWT_SECRET_KEY", "e2e-test-secret-key-e2e-test-secret-key-e2e-x")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

# Must import AFTER env vars are set (config uses lru_cache)
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from backend.shared.text import vi_unaccent
from backend.shared.models import Base

# Import all models so Base.metadata knows about every table
from backend.modules.tenant.models import Tenant  # noqa
from backend.modules.auth.models import User, RefreshToken  # noqa
from backend.modules.product.models import Category, Product, ProductImage, ProductUnit  # noqa
from backend.modules.customer.models import Customer, Supplier  # noqa
from backend.modules.inventory.models import GoodsReceipt, GoodsReceiptItem, Inventory, StockMovement  # noqa
from backend.modules.sales.models import Invoice, InvoiceItem, Payment, ReturnOrder, ReturnOrderItem  # noqa
from backend.modules.cashbook.models import CashTransaction  # noqa
from backend.modules.system.models import AuditLog, PriceHistory  # noqa
from backend.shared.code_generator import CodeSequence  # noqa


async def init_db() -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_funcs(dbapi_conn, _):
        dbapi_conn.create_function("immutable_unaccent", 1, vi_unaccent)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


asyncio.run(init_db())

import uvicorn
uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="warning")
