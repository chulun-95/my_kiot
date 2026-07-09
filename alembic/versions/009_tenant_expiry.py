"""add expires_at to tenants

Revision ID: 009_tenant_expiry
Revises: 008_receipt_payment_method
Create Date: 2026-07-09 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_tenant_expiry"
down_revision: Union[str, None] = "008_receipt_payment_method"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "expires_at")
