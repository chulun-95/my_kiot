from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.models import Base, AuditMixin, SoftDeleteMixin
from backend.shared.types import FKType, PKType


class Category(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "categories"
    __table_args__ = (
        Index(
            "idx_categories_tenant",
            "tenant_id",
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    depth: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default="1"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="save-update",
    )
    parent: Mapped["Category | None"] = relationship(
        "Category", back_populates="children", remote_side="Category.id"
    )


class Product(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "products"
    __table_args__ = (
        Index(
            "uq_products_tenant_sku",
            "tenant_id",
            "sku",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_products_tenant_barcode",
            "tenant_id",
            "barcode",
            unique=True,
            sqlite_where=text("deleted_at IS NULL AND barcode IS NOT NULL"),
            postgresql_where=text("deleted_at IS NULL AND barcode IS NOT NULL"),
        ),
        Index("idx_products_tenant_status", "tenant_id", "status"),
        Index("idx_products_tenant_category", "tenant_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("categories.id"), nullable=True
    )
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(
        String(30), nullable=False, default="cái", server_default="cái"
    )
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    min_stock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    allow_negative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        FKType, ForeignKey("users.id"), nullable=True
    )

    category: Mapped["Category | None"] = relationship("Category", lazy="joined")
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    units: Mapped[list["ProductUnit"]] = relationship(
        "ProductUnit",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductUnit.unit_name",
        lazy="selectin",
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        FKType,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    product: Mapped["Product"] = relationship("Product", back_populates="images")


class ProductUnit(Base):
    __tablename__ = "product_units"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "product_id", "unit_name",
            name="uq_product_units_tenant_product_unit",
        ),
        Index(
            "uq_product_units_tenant_barcode",
            "tenant_id",
            "barcode",
            unique=True,
            sqlite_where=text("barcode IS NOT NULL"),
            postgresql_where=text("barcode IS NOT NULL"),
        ),
        Index("idx_product_units_product", "tenant_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    unit_name: Mapped[str] = mapped_column(String(30), nullable=False)
    conversion_rate: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    sale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    product: Mapped["Product"] = relationship("Product", back_populates="units")
