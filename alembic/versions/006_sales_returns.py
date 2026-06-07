"""add return_orders + return_order_items

Revision ID: 006_sales_returns
Revises: 005_cash_book
Create Date: 2026-06-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_sales_returns"
down_revision: Union[str, None] = "005_cash_book"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "return_orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("cashier_id", sa.BigInteger(), nullable=False),
        sa.Column("subtotal", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("total_refund", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("cost_total", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("refund_method", sa.String(length=20), server_default="CASH", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="COMPLETED", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.BigInteger(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_return_orders_tenant_code"),
    )
    op.create_index("ix_return_orders_tenant_id", "return_orders", ["tenant_id"])
    op.create_index("idx_return_orders_tenant_completed", "return_orders", ["tenant_id", "completed_at"])
    op.create_index("idx_return_orders_invoice", "return_orders", ["tenant_id", "invoice_id"])

    op.create_table(
        "return_order_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.BigInteger(), nullable=False),
        sa.Column("invoice_item_id", sa.BigInteger(), nullable=True),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("product_name", sa.String(length=300), nullable=False),
        sa.Column("product_sku", sa.String(length=50), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("line_total", sa.Numeric(15, 2), nullable=False),
        sa.Column("unit_id", sa.BigInteger(), nullable=True),
        sa.Column("conversion_rate", sa.Numeric(10, 3), nullable=True),
        sa.ForeignKeyConstraint(["return_id"], ["return_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_item_id"], ["invoice_items.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["product_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_return_order_items_return_id", "return_order_items", ["return_id"])


def downgrade() -> None:
    op.drop_index("ix_return_order_items_return_id", "return_order_items")
    op.drop_table("return_order_items")
    op.drop_index("idx_return_orders_invoice", "return_orders")
    op.drop_index("idx_return_orders_tenant_completed", "return_orders")
    op.drop_index("ix_return_orders_tenant_id", "return_orders")
    op.drop_table("return_orders")
