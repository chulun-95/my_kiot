from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import Base, AuditMixin
from backend.shared.types import FKType, PKType


class GoodsReceipt(Base, AuditMixin):
    __tablename__ = "goods_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_goods_receipts_tenant_code"),
        Index(
            "idx_goods_receipts_tenant_completed",
            "tenant_id",
            "completed_at",
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    supplier_id: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("suppliers.id"), nullable=True
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    # Phương thức trả tiền nhập: CASH | BANK_TRANSFER | EWALLET
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CASH", server_default="CASH"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", server_default="DRAFT"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("users.id"), nullable=True
    )

    items: Mapped[list["GoodsReceiptItem"]] = relationship(
        "GoodsReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )


class GoodsReceiptItem(Base):
    __tablename__ = "goods_receipt_items"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(
        FKType,
        ForeignKey("goods_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    unit_id: Mapped[Optional[int]] = mapped_column(
        FKType,
        ForeignKey("product_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    unit_name: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    conversion_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3), nullable=True)

    receipt: Mapped["GoodsReceipt"] = relationship(
        "GoodsReceipt", back_populates="items"
    )


class StockMovement(Base):
    """Kardex — APPEND-ONLY. Không UPDATE/DELETE."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        Index(
            "idx_stock_movements_kardex",
            "tenant_id",
            "product_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_id: Mapped[int] = mapped_column(FKType, nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int] = mapped_column(
        FKType, ForeignKey("users.id"), nullable=False
    )


class Inventory(Base):
    """Cache tồn kho — derived từ SUM(stock_movements.quantity).
    Có thể rebuild bất kỳ lúc nào.
    """

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "product_id", name="uq_inventory_tenant_product"
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
