"""add product_units table and unit columns to receipt/invoice items

Revision ID: 003_product_units
Revises: 002_phase2_to_5
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "003_product_units"
down_revision: Union[str, None] = "002_phase2_to_5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_units",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("unit_name", sa.String(length=30), nullable=False),
        sa.Column("conversion_rate", sa.Numeric(10, 3), nullable=False),
        sa.Column("sale_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("barcode", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "product_id", "unit_name",
            name="uq_product_units_tenant_product_unit",
        ),
    )
    op.create_index(
        "idx_product_units_product", "product_units", ["tenant_id", "product_id"]
    )
    op.create_index(
        "uq_product_units_tenant_barcode",
        "product_units",
        ["tenant_id", "barcode"],
        unique=True,
        postgresql_where=sa.text("barcode IS NOT NULL"),
        sqlite_where=sa.text("barcode IS NOT NULL"),
    )

    # goods_receipt_items — add 3 columns
    op.add_column("goods_receipt_items", sa.Column("unit_id", sa.BigInteger(), nullable=True))
    op.add_column("goods_receipt_items", sa.Column("unit_name", sa.String(length=30), nullable=True))
    op.add_column("goods_receipt_items", sa.Column("conversion_rate", sa.Numeric(10, 3), nullable=True))
    op.create_foreign_key(
        "fk_gri_unit_id",
        "goods_receipt_items", "product_units",
        ["unit_id"], ["id"],
        ondelete="SET NULL",
    )

    # invoice_items — add 2 columns
    op.add_column("invoice_items", sa.Column("unit_id", sa.BigInteger(), nullable=True))
    op.add_column("invoice_items", sa.Column("conversion_rate", sa.Numeric(10, 3), nullable=True))
    op.create_foreign_key(
        "fk_ii_unit_id",
        "invoice_items", "product_units",
        ["unit_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ii_unit_id", "invoice_items", type_="foreignkey")
    op.drop_column("invoice_items", "conversion_rate")
    op.drop_column("invoice_items", "unit_id")

    op.drop_constraint("fk_gri_unit_id", "goods_receipt_items", type_="foreignkey")
    op.drop_column("goods_receipt_items", "conversion_rate")
    op.drop_column("goods_receipt_items", "unit_name")
    op.drop_column("goods_receipt_items", "unit_id")

    op.drop_index("uq_product_units_tenant_barcode", "product_units")
    op.drop_index("idx_product_units_product", "product_units")
    op.drop_table("product_units")
