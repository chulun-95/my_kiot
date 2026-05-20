import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-test-secret-key-test-secret-key-x")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("APP_ENV", "test")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import get_db
from backend.main import app
from backend.shared.models import Base
from backend.modules.tenant.models import Tenant  # noqa: F401
from backend.modules.auth.models import User, RefreshToken  # noqa: F401


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    session_factory = async_sessionmaker(
        db_engine, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncClient:
    session_factory = async_sessionmaker(
        db_engine, expire_on_commit=False, autoflush=False
    )

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _override_get_db
    # Disable slowapi rate limiter in tests
    app.state.limiter.enabled = False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_owner(client) -> dict:
    payload = {
        "shop_name": "Tap Hoa Test",
        "owner_name": "Owner Test",
        "phone": "0901234567",
        "password": "secret123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    data["password"] = payload["password"]
    data["phone"] = payload["phone"]
    return data


def auth_header(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}
