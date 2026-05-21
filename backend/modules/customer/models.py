from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.models import Base, AuditMixin, SoftDeleteMixin
from backend.shared.types import FKType, PKType


class Customer(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "customers"
    __table_args__ = (
        Index(
            "uq_customers_tenant_phone",
            "tenant_id",
            "phone",
            unique=True,
            sqlite_where=text("deleted_at IS NULL AND phone IS NOT NULL"),
            postgresql_where=text("deleted_at IS NULL AND phone IS NOT NULL"),
        ),
        Index("idx_customers_tenant", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_spent: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_order_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Supplier(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "suppliers"
    __table_args__ = (Index("idx_suppliers_tenant", "tenant_id"),)

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_debt: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
