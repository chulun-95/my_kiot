from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.modules.auth.models import User
from backend.modules.auth.utils import hash_password
from backend.modules.tenant.models import Tenant
from backend.modules.system.models import AuditLog
from backend.scripts.extend_tenant import extend_tenant
from backend.shared import audit as audit_helper
from backend.shared.dates import add_months

pytestmark = pytest.mark.asyncio


async def _create_tenant_with_owner(db_session, *, phone: str, expires_at) -> tuple[Tenant, User]:
    tenant = Tenant(name="Shop Test", slug=f"shop-{phone}", expires_at=expires_at)
    db_session.add(tenant)
    await db_session.flush()

    owner = User(
        tenant_id=tenant.id,
        phone=phone,
        email=None,
        full_name="Chu Shop",
        password_hash=hash_password("secret123"),
        role="OWNER",
        is_active=True,
    )
    db_session.add(owner)
    await db_session.flush()
    await db_session.commit()
    return tenant, owner


async def test_extend_tenant_accumulates_when_still_active(db_session):
    now = datetime.now(tz=timezone.utc)
    old_expiry = now + timedelta(days=60)
    tenant, _ = await _create_tenant_with_owner(
        db_session, phone="0911111111", expires_at=old_expiry
    )

    updated = await extend_tenant(db_session, "0911111111", months=6)

    expected = add_months(old_expiry, 6)
    assert abs((updated.expires_at.replace(tzinfo=timezone.utc) - expected).total_seconds()) < 5


async def test_extend_tenant_counts_from_now_when_already_expired(db_session):
    now = datetime.now(tz=timezone.utc)
    old_expiry = now - timedelta(days=30)
    tenant, _ = await _create_tenant_with_owner(
        db_session, phone="0922222222", expires_at=old_expiry
    )

    before_call = datetime.now(tz=timezone.utc)
    updated = await extend_tenant(db_session, "0922222222", months=6)

    expected = add_months(before_call, 6)
    assert abs((updated.expires_at.replace(tzinfo=timezone.utc) - expected).total_seconds()) < 5


async def test_extend_tenant_defaults_to_six_months(db_session):
    now = datetime.now(tz=timezone.utc)
    tenant, _ = await _create_tenant_with_owner(
        db_session, phone="0933333333", expires_at=now
    )

    before_call = datetime.now(tz=timezone.utc)
    updated = await extend_tenant(db_session, "0933333333")

    expected = add_months(before_call, 6)
    assert abs((updated.expires_at.replace(tzinfo=timezone.utc) - expected).total_seconds()) < 5


async def test_extend_tenant_writes_single_audit_row(db_session):
    now = datetime.now(tz=timezone.utc)
    tenant, owner = await _create_tenant_with_owner(
        db_session, phone="0944444444", expires_at=now
    )

    await extend_tenant(db_session, "0944444444", months=3)

    rows = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == tenant.id,
                AuditLog.action == audit_helper.EXTEND_SUBSCRIPTION,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    log = rows[0]
    assert log.entity_type == "tenant"
    assert log.entity_id == tenant.id
    assert log.user_id == owner.id
    assert log.new_data["months"] == 3
    assert "new_expires_at" in log.new_data


async def test_extend_tenant_unknown_phone_raises_value_error(db_session):
    with pytest.raises(ValueError):
        await extend_tenant(db_session, "0999999999", months=6)
