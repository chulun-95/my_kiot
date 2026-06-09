"""add payment_method to goods_receipts

Revision ID: 008_receipt_payment_method
Revises: 007_return_debt_adjust
Create Date: 2026-06-09 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_receipt_payment_method"
down_revision: Union[str, None] = "007_return_debt_adjust"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "goods_receipts",
        sa.Column("payment_method", sa.String(length=20), server_default="CASH", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("goods_receipts", "payment_method")
