"""Script gia hạn thủ công gói dịch vụ cho 1 tenant.

Chạy tay trên VPS bởi admin (chủ hệ thống) khi khách liên hệ gia hạn qua
Zalo/Facebook. Không có endpoint HTTP tương ứng — chỉ chạy CLI.

Cách chạy:

    python -m backend.scripts.extend_tenant --phone 0912345678 --months 6
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session_maker
from backend.modules.auth.models import User
from backend.modules.tenant.models import Tenant
from backend.shared import audit as audit_helper
from backend.shared.dates import add_months


async def extend_tenant(db: AsyncSession, phone: str, months: int = 6) -> Tenant:
    """Tìm tenant qua SĐT chủ shop (role OWNER), gia hạn expires_at, ghi audit log.

    Raise ValueError nếu không tìm thấy chủ shop nào khớp SĐT.
    """
    owner = await db.scalar(
        select(User).where(
            User.phone == phone,
            User.role == "OWNER",
            User.deleted_at.is_(None),
        )
    )
    if owner is None:
        raise ValueError(f"Không tìm thấy chủ shop với số điện thoại {phone}")

    tenant = await db.get(Tenant, owner.tenant_id)
    if tenant is None:
        raise ValueError(f"Không tìm thấy tenant cho chủ shop {phone}")

    now = datetime.now(tz=timezone.utc)
    expires_at = tenant.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    base = expires_at if expires_at and expires_at > now else now

    tenant.expires_at = add_months(base, months)

    await audit_helper.write_audit(
        db,
        tenant_id=tenant.id,
        user_id=owner.id,
        action=audit_helper.EXTEND_SUBSCRIPTION,
        entity_type="tenant",
        entity_id=tenant.id,
        new_data={
            "months": months,
            "new_expires_at": tenant.expires_at.isoformat(),
        },
    )

    await db.commit()
    await db.refresh(tenant)
    return tenant


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Gia hạn gói dịch vụ cho 1 shop theo số điện thoại chủ shop."
    )
    parser.add_argument("--phone", required=True, help="Số điện thoại chủ shop (OWNER)")
    parser.add_argument(
        "--months", type=int, default=6, help="Số tháng gia hạn (mặc định 6)"
    )
    args = parser.parse_args()

    async with async_session_maker() as db:
        tenant = await extend_tenant(db, args.phone, args.months)

    expires_str = tenant.expires_at.strftime("%d/%m/%Y") if tenant.expires_at else "?"
    print(f"Đã gia hạn shop '{tenant.name}' — hạn dùng mới: {expires_str}")


if __name__ == "__main__":
    asyncio.run(_main())
