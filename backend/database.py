from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# SQLite (used in tests) needs custom functions that PostgreSQL provides natively.
if settings.DATABASE_URL.startswith("sqlite"):
    from backend.shared.text import vi_unaccent

    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_funcs(dbapi_conn, _):
        dbapi_conn.create_function("immutable_unaccent", 1, vi_unaccent)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
