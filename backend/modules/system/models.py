from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.models import Base
from backend.shared.types import FKType, PKType


JSONType = JSONB().with_variant(JSON(), "sqlite")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index(
            "idx_audit_logs_entity",
            "tenant_id",
            "entity_type",
            "entity_id",
            "created_at",
        ),
        Index("idx_audit_logs_tenant_action", "tenant_id", "action"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(FKType, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(FKType, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(FKType, nullable=True)
    old_data: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    new_data: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        Index(
            "idx_price_history_product",
            "tenant_id",
            "product_id",
            "changed_at",
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(FKType, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("products.id"), nullable=False
    )
    field: Mapped[str] = mapped_column(String(20), nullable=False)
    old_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    new_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_id: Mapped[Optional[int]] = mapped_column(FKType, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("users.id"), nullable=True
    )
