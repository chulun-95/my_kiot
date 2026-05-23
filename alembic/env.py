import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import settings  # noqa: E402
from backend.shared.models import Base  # noqa: E402
from backend.modules.tenant.models import Tenant  # noqa: F401,E402
from backend.modules.auth.models import User, RefreshToken  # noqa: F401,E402
from backend.modules.product.models import (  # noqa: F401,E402
    Category,
    Product,
    ProductImage,
)
from backend.modules.customer.models import Customer, Supplier  # noqa: F401,E402
from backend.modules.inventory.models import (  # noqa: F401,E402
    GoodsReceipt,
    GoodsReceiptItem,
    Inventory,
    StockMovement,
)
from backend.modules.sales.models import (  # noqa: F401,E402
    Invoice,
    InvoiceItem,
    Payment,
)
from backend.modules.system.models import AuditLog, PriceHistory  # noqa: F401,E402
from backend.shared.code_generator import CodeSequence  # noqa: F401,E402


config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
