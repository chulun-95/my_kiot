"""add debt_adjust + cash_refund to return_orders

Revision ID: 007_return_debt_adjust
Revises: 006_sales_returns
Create Date: 2026-06-08 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_return_debt_adjust"
down_revision: Union[str, None] = "006_sales_returns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "return_orders",
        sa.Column("debt_adjust", sa.Numeric(15, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "return_orders",
        sa.Column("cash_refund", sa.Numeric(15, 2), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("return_orders", "cash_refund")
    op.drop_column("return_orders", "debt_adjust")
