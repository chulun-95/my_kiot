from datetime import datetime, timezone, timedelta

from sqlalchemy import Integer, String, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.models import Base
from backend.shared.types import FKType, PKType


VN_TZ = timezone(timedelta(hours=7))


class CodeSequence(Base):
    __tablename__ = "code_sequences"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "prefix", "date_part", name="uq_code_sequences"
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(FKType, nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    date_part: Mapped[str] = mapped_column(
        String(8), nullable=False, default="", server_default=""
    )
    last_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


async def generate_code(
    db: AsyncSession,
    tenant_id: int,
    prefix: str,
    with_date: bool = True,
) -> str:
    """Sinh mã tự động dạng `{prefix}{date}-{NNN}` hoặc `{prefix}{NNNNNN}`.

    - with_date=True  → HD20260517-001 (cho hóa đơn, phiếu nhập)
    - with_date=False → SP000001 (cho SKU sản phẩm)
    """
    date_part = datetime.now(tz=VN_TZ).strftime("%Y%m%d") if with_date else ""

    stmt = (
        select(CodeSequence)
        .where(
            CodeSequence.tenant_id == tenant_id,
            CodeSequence.prefix == prefix,
            CodeSequence.date_part == date_part,
        )
        .with_for_update()
    )
    seq = await db.scalar(stmt)

    if seq is None:
        seq = CodeSequence(
            tenant_id=tenant_id,
            prefix=prefix,
            date_part=date_part,
            last_number=1,
        )
        db.add(seq)
        await db.flush()
        number = 1
    else:
        seq.last_number += 1
        await db.flush()
        number = seq.last_number

    if date_part:
        return f"{prefix}{date_part}-{number:03d}"
    return f"{prefix}{number:06d}"
