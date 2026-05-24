"""enable unaccent extension and add functional trigram index for diacritic-insensitive product search

Revision ID: 004_unaccent_search
Revises: 003_product_units
Create Date: 2026-05-24 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "004_unaccent_search"
down_revision: Union[str, None] = "003_product_units"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # unaccent strips Vietnamese diacritics (đ → d, ữ → u, ô → o, ...)
    # so "Sữa" matches search "sua" and "Mỳ tôm" matches "my tom".
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    # Functional GIN trigram index — must wrap unaccent() in IMMUTABLE wrapper
    # because unaccent is STABLE by default (depends on session settings).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION immutable_unaccent(text) RETURNS text AS
        $$ SELECT public.unaccent('public.unaccent', $1) $$
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        """
    )

    op.execute(
        """
        CREATE INDEX idx_products_name_unaccent_trgm
          ON products
          USING gin (immutable_unaccent(lower(name)) gin_trgm_ops)
          WHERE deleted_at IS NULL
        """
    )

    op.execute(
        """
        CREATE INDEX idx_customers_name_unaccent_trgm
          ON customers
          USING gin (immutable_unaccent(lower(name)) gin_trgm_ops)
          WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_customers_name_unaccent_trgm")
    op.execute("DROP INDEX IF EXISTS idx_products_name_unaccent_trgm")
    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
    # Leave unaccent extension in place — other migrations / functions may use it.
