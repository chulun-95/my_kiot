import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.modules.product.models import Category
from backend.modules.tenant.models import Tenant

MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic" / "versions" / "010_backfill_default_categories.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_010_backfill_default_categories", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_backfill_seeds_tenant_without_any_category(db_session):
    migration = _load_migration()

    tenant = Tenant(name="Shop Cu Chua Co Cat", slug="shop-cu-chua-co-cat", address="1 A")
    db_session.add(tenant)
    await db_session.flush()

    def _run(sync_session):
        conn = sync_session.connection()
        migration._backfill(conn)

    await db_session.run_sync(_run)
    await db_session.commit()

    rows = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant.id))
    ).scalars().all()
    assert len(rows) == 21

    by_name = {c.name: c for c in rows}
    assert by_name["Đồ uống"].depth == 1
    assert by_name["Nước ngọt & Tăng lực"].parent_id == by_name["Đồ uống"].id


@pytest.mark.asyncio
async def test_backfill_skips_tenant_with_existing_category(db_session):
    migration = _load_migration()

    tenant = Tenant(name="Shop Da Co Cat", slug="shop-da-co-cat", address="2 B")
    db_session.add(tenant)
    await db_session.flush()
    existing = Category(tenant_id=tenant.id, name="Tự Tạo", depth=1, sort_order=0)
    db_session.add(existing)
    await db_session.flush()

    def _run(sync_session):
        conn = sync_session.connection()
        migration._backfill(conn)

    await db_session.run_sync(_run)
    await db_session.commit()

    rows = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant.id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "Tự Tạo"


@pytest.mark.asyncio
async def test_backfill_isolates_between_tenants(db_session):
    migration = _load_migration()

    tenant_a = Tenant(name="Shop Old A", slug="shop-old-a", address="3 C")
    tenant_b = Tenant(name="Shop Old B", slug="shop-old-b", address="4 D")
    db_session.add_all([tenant_a, tenant_b])
    await db_session.flush()

    def _run(sync_session):
        conn = sync_session.connection()
        migration._backfill(conn)

    await db_session.run_sync(_run)
    await db_session.commit()

    rows_a = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant_a.id))
    ).scalars().all()
    rows_b = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant_b.id))
    ).scalars().all()
    assert len(rows_a) == 21
    assert len(rows_b) == 21
    ids_a = {c.id for c in rows_a}
    ids_b = {c.id for c in rows_b}
    assert ids_a.isdisjoint(ids_b)
