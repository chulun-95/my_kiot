"""add cash_transactions table (cash book)

Revision ID: 005_cash_book
Revises: 004_unaccent_search
Create Date: 2026-06-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "005_cash_book"
down_revision: Union[str, None] = "004_unaccent_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cash_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("direction", sa.String(length=3), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("ref_type", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        sa.Column("partner_type", sa.String(length=20), nullable=True),
        sa.Column("partner_id", sa.BigInteger(), nullable=True),
        sa.Column("partner_name", sa.String(length=200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.BigInteger(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_cash_tx_tenant_code"),
    )
    op.create_index("idx_cash_tx_tenant_created", "cash_transactions", ["tenant_id", "created_at"])
    op.create_index("idx_cash_tx_tenant_dir", "cash_transactions", ["tenant_id", "direction", "created_at"])
    op.create_index("idx_cash_tx_ref", "cash_transactions", ["tenant_id", "ref_type", "ref_id"])
    op.create_index("ix_cash_transactions_tenant_id", "cash_transactions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_cash_transactions_tenant_id", "cash_transactions")
    op.drop_index("idx_cash_tx_ref", "cash_transactions")
    op.drop_index("idx_cash_tx_tenant_dir", "cash_transactions")
    op.drop_index("idx_cash_tx_tenant_created", "cash_transactions")
    op.drop_table("cash_transactions")
