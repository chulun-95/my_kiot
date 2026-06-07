from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.models import Base
from backend.shared.types import FKType, PKType


class CashTransaction(Base):
    """Sổ quỹ — phiếu thu/chi. Append-only; hủy bằng status=CANCELLED."""

    __tablename__ = "cash_transactions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_cash_tx_tenant_code"),
        Index("idx_cash_tx_tenant_created", "tenant_id", "created_at"),
        Index("idx_cash_tx_tenant_dir", "tenant_id", "direction", "created_at"),
        Index("idx_cash_tx_ref", "tenant_id", "ref_type", "ref_id"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)  # IN | OUT
    method: Mapped[str] = mapped_column(String(20), nullable=False)    # CASH|BANK_TRANSFER|EWALLET
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    ref_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MANUAL", server_default="MANUAL"
    )
    ref_id: Mapped[Optional[int]] = mapped_column(FKType, nullable=True)
    partner_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    partner_id: Mapped[Optional[int]] = mapped_column(FKType, nullable=True)
    partner_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("users.id"), nullable=True
    )
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("users.id"), nullable=True
    )
