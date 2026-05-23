"""phase 2-5 schema: products, customers, inventory, sales, system

Revision ID: 002_phase2_to_5
Revises: 001_initial
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "002_phase2_to_5"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Trigram extension cho POS autocomplete (tên SP/KH)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ================================================================
    # MASTER DATA — Categories, Products, Product images
    # ================================================================
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("depth", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("depth IN (1, 2)", name="ck_categories_depth"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_categories_tenant", "categories", ["tenant_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("barcode", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=30), server_default="cái", nullable=False),
        sa.Column(
            "cost_price", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "sale_price", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column("min_stock", sa.Integer(), server_default="0", nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default="ACTIVE", nullable=False
        ),
        sa.Column(
            "allow_negative",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_products_tenant", "products", ["tenant_id"])
    op.create_index(
        "idx_products_tenant_status", "products", ["tenant_id", "status"]
    )
    op.create_index(
        "idx_products_tenant_category", "products", ["tenant_id", "category_id"]
    )
    op.create_index(
        "uq_products_tenant_sku",
        "products",
        ["tenant_id", "sku"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_products_tenant_barcode",
        "products",
        ["tenant_id", "barcode"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND barcode IS NOT NULL"
        ),
    )
    # GIN trigram cho POS gõ tên SP gợi ý
    op.execute(
        "CREATE INDEX idx_products_name_trgm ON products "
        "USING gin (name gin_trgm_ops) WHERE deleted_at IS NULL"
    )

    op.create_table(
        "product_images",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_product_images_product", "product_images", ["product_id"])

    # ================================================================
    # MASTER DATA — Customers, Suppliers
    # ================================================================
    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "total_spent", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "total_orders", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "last_order_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_customers_tenant", "customers", ["tenant_id"])
    op.create_index(
        "uq_customers_tenant_phone",
        "customers",
        ["tenant_id", "phone"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND phone IS NOT NULL"
        ),
    )
    op.execute(
        "CREATE INDEX idx_customers_name_trgm ON customers "
        "USING gin (name gin_trgm_ops) WHERE deleted_at IS NULL"
    )

    op.create_table(
        "suppliers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("tax_code", sa.String(length=20), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "total_debt", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_suppliers_tenant", "suppliers", ["tenant_id"])

    # ================================================================
    # INVENTORY — Goods receipts, Stock movements, Inventory cache
    # ================================================================
    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "total", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "paid_amount", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "status", sa.String(length=20), server_default="DRAFT", nullable=False
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "code", name="uq_goods_receipts_tenant_code"
        ),
    )
    op.create_index("idx_goods_receipts_tenant", "goods_receipts", ["tenant_id"])
    op.create_index(
        "idx_goods_receipts_tenant_completed",
        "goods_receipts",
        ["tenant_id", "completed_at"],
        postgresql_where=sa.text("status = 'COMPLETED'"),
    )

    op.create_table(
        "goods_receipt_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("receipt_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("cost_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(15, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["receipt_id"], ["goods_receipts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_goods_receipt_items_receipt", "goods_receipt_items", ["receipt_id"]
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("ref_type", sa.String(length=20), nullable=False),
        sa.Column("ref_id", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.Numeric(10, 3), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_stock_movements_tenant", "stock_movements", ["tenant_id"])
    op.create_index(
        "idx_stock_movements_kardex",
        "stock_movements",
        ["tenant_id", "product_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "inventory",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "quantity", sa.Numeric(10, 3), server_default="0", nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "product_id", name="uq_inventory_tenant_product"
        ),
    )
    op.create_index("idx_inventory_tenant", "inventory", ["tenant_id"])

    # ================================================================
    # SALES — Invoices, Items, Payments
    # ================================================================
    op.create_table(
        "invoices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("cashier_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "subtotal", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "discount_amount",
            sa.Numeric(15, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("total", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column(
            "cost_total", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "paid_amount", sa.Numeric(15, 2), server_default="0", nullable=False
        ),
        sa.Column(
            "change_amount",
            sa.Numeric(15, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=20), server_default="DRAFT", nullable=False
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.BigInteger(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_invoices_tenant_code"),
    )
    op.create_index("idx_invoices_tenant", "invoices", ["tenant_id"])
    op.create_index(
        "idx_invoices_tenant_completed",
        "invoices",
        ["tenant_id", sa.text("completed_at DESC")],
        postgresql_where=sa.text("status = 'COMPLETED'"),
    )
    op.create_index(
        "idx_invoices_tenant_customer",
        "invoices",
        ["tenant_id", "customer_id", sa.text("completed_at DESC")],
        postgresql_where=sa.text(
            "status = 'COMPLETED' AND customer_id IS NOT NULL"
        ),
    )
    op.create_index(
        "idx_invoices_drafts",
        "invoices",
        ["tenant_id", "cashier_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("status = 'DRAFT'"),
    )

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("product_name", sa.String(length=300), nullable=False),
        sa.Column("product_sku", sa.String(length=50), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "discount_amount",
            sa.Numeric(15, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("line_total", sa.Numeric(15, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_invoice_items_invoice", "invoice_items", ["invoice_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_payments_invoice", "payments", ["invoice_id"])

    # ================================================================
    # SYSTEM — Audit logs, Price history, Code sequences
    # ================================================================
    # audit_logs: tenant_id/user_id KHÔNG là FK — log phải sống sót khi xóa entity
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "old_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "new_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_tenant", "audit_logs", ["tenant_id"])
    op.create_index(
        "idx_audit_logs_entity",
        "audit_logs",
        ["tenant_id", "entity_type", "entity_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_audit_logs_tenant_action", "audit_logs", ["tenant_id", "action"]
    )

    # price_history: FK product_id + changed_by; tenant_id/ref_id KHÔNG là FK
    op.create_table(
        "price_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("field", sa.String(length=20), nullable=False),
        sa.Column("old_value", sa.Numeric(15, 2), nullable=True),
        sa.Column("new_value", sa.Numeric(15, 2), nullable=False),
        sa.Column("ref_type", sa.String(length=20), nullable=False),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("changed_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_price_history_tenant", "price_history", ["tenant_id"])
    op.create_index(
        "idx_price_history_product",
        "price_history",
        ["tenant_id", "product_id", sa.text("changed_at DESC")],
    )

    # code_sequences: KHÔNG có FK trong model — match nguyên gốc
    op.create_table(
        "code_sequences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("prefix", sa.String(length=10), nullable=False),
        sa.Column(
            "date_part", sa.String(length=8), server_default="", nullable=False
        ),
        sa.Column(
            "last_number", sa.Integer(), server_default="0", nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "prefix", "date_part", name="uq_code_sequences"
        ),
    )
    op.create_index("idx_code_sequences_tenant", "code_sequences", ["tenant_id"])


def downgrade() -> None:
    # Drop theo thứ tự ngược FK dependency
    op.drop_index("idx_code_sequences_tenant", table_name="code_sequences")
    op.drop_table("code_sequences")

    op.drop_index("idx_price_history_product", table_name="price_history")
    op.drop_index("idx_price_history_tenant", table_name="price_history")
    op.drop_table("price_history")

    op.drop_index("idx_audit_logs_tenant_action", table_name="audit_logs")
    op.drop_index("idx_audit_logs_entity", table_name="audit_logs")
    op.drop_index("idx_audit_logs_tenant", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("idx_payments_invoice", table_name="payments")
    op.drop_table("payments")

    op.drop_index("idx_invoice_items_invoice", table_name="invoice_items")
    op.drop_table("invoice_items")

    op.drop_index("idx_invoices_drafts", table_name="invoices")
    op.drop_index("idx_invoices_tenant_customer", table_name="invoices")
    op.drop_index("idx_invoices_tenant_completed", table_name="invoices")
    op.drop_index("idx_invoices_tenant", table_name="invoices")
    op.drop_table("invoices")

    op.drop_index("idx_inventory_tenant", table_name="inventory")
    op.drop_table("inventory")

    op.drop_index("idx_stock_movements_kardex", table_name="stock_movements")
    op.drop_index("idx_stock_movements_tenant", table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index(
        "idx_goods_receipt_items_receipt", table_name="goods_receipt_items"
    )
    op.drop_table("goods_receipt_items")

    op.drop_index(
        "idx_goods_receipts_tenant_completed", table_name="goods_receipts"
    )
    op.drop_index("idx_goods_receipts_tenant", table_name="goods_receipts")
    op.drop_table("goods_receipts")

    op.drop_index("idx_suppliers_tenant", table_name="suppliers")
    op.drop_table("suppliers")

    op.execute("DROP INDEX IF EXISTS idx_customers_name_trgm")
    op.drop_index("uq_customers_tenant_phone", table_name="customers")
    op.drop_index("idx_customers_tenant", table_name="customers")
    op.drop_table("customers")

    op.drop_index("idx_product_images_product", table_name="product_images")
    op.drop_table("product_images")

    op.execute("DROP INDEX IF EXISTS idx_products_name_trgm")
    op.drop_index("uq_products_tenant_barcode", table_name="products")
    op.drop_index("uq_products_tenant_sku", table_name="products")
    op.drop_index("idx_products_tenant_category", table_name="products")
    op.drop_index("idx_products_tenant_status", table_name="products")
    op.drop_index("idx_products_tenant", table_name="products")
    op.drop_table("products")

    op.drop_index("idx_categories_tenant", table_name="categories")
    op.drop_table("categories")

    # Extension giữ lại — có thể bị extension khác phụ thuộc.
    # Nếu muốn xóa hoàn toàn: op.execute("DROP EXTENSION IF EXISTS pg_trgm")
