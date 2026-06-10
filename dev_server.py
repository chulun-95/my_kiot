"""
Local dev backend on SQLite (no Postgres/Docker needed).
Run:  .venv\\Scripts\\python.exe dev_server.py
Serves http://127.0.0.1:8000  (Vite proxies /api -> here)
Creates tables if missing; does NOT drop existing data (persistent dev.db).
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "dev.db"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")
os.environ.setdefault("JWT_SECRET_KEY", "dev-local-secret-key-dev-local-secret-key-dev-x")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from backend.shared.text import vi_unaccent
from backend.shared.models import Base

# Import all models so Base.metadata knows every table
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
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


asyncio.run(init_db())

import uvicorn
print(f"[dev_server] SQLite DB: {DB_PATH}")
print("[dev_server] http://127.0.0.1:8000  (docs at /docs)")
uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info")
