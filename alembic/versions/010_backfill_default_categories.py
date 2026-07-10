"""backfill default categories for tenants without any category

Revision ID: 010_backfill_default_categories
Revises: 009_tenant_expiry
Create Date: 2026-07-10 00:00:00.000000
"""
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_backfill_default_categories"
down_revision: Union[str, None] = "009_tenant_expiry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Snapshot cố định tại thời điểm viết migration — KHÔNG import từ backend/shared/, vì
# migration phải ổn định theo thời gian, độc lập với danh sách trong code app có thể đổi sau.
_CATEGORIES: list[tuple[str, str, int, str | None]] = [
    ("do_uong", "Đồ uống", 1, None),
    ("nc_ngot", "Nước ngọt & Tăng lực", 2, "do_uong"),
    ("bia_ruou", "Bia & Rượu", 2, "do_uong"),
    ("nc_chai", "Nước đóng chai & Trà", 2, "do_uong"),
    ("tp_kho", "Thực phẩm khô", 1, None),
    ("mi_bun", "Mì tôm & Bún khô", 2, "tp_kho"),
    ("gao_bot", "Gạo & Bột", 2, "tp_kho"),
    ("gia_vi", "Gia vị & Dầu ăn", 1, None),
    ("bk_snack", "Bánh kẹo & Snack", 1, None),
    ("snack_bq", "Snack & Bánh quy", 2, "bk_snack"),
    ("keo_choco", "Kẹo & Chocolate", 2, "bk_snack"),
    ("sua", "Sữa & Sản phẩm sữa", 1, None),
    ("sua_tuoi", "Sữa tươi & Đóng hộp", 2, "sua"),
    ("sua_chua", "Sữa chua & Phô mai", 2, "sua"),
    ("cs_cn", "Chăm sóc cá nhân", 1, None),
    ("ve_sinh", "Vệ sinh cá nhân", 2, "cs_cn"),
    ("dau_goi", "Dầu gội & Dưỡng da", 2, "cs_cn"),
    ("dd_gd", "Đồ dùng gia đình", 1, None),
    ("tay_rua", "Tẩy rửa", 2, "dd_gd"),
    ("dung_cu", "Dụng cụ & Tiện ích", 2, "dd_gd"),
    ("thuoc_la", "Thuốc lá & Diêm quẹt", 1, None),
]


def _backfill(conn) -> None:
    """Thân logic tách riêng khỏi upgrade() để test gọi trực tiếp qua 1 connection
    (kể cả connection của DB test SQLite) — không cần chạy qua toàn bộ Alembic chain.

    Dùng bind-param truyền timestamp Python (KHÔNG gọi NOW() trong SQL) vì SQLite (DB test)
    không có hàm NOW() — Postgres (production) và SQLite đều nhận bind-param như nhau.
    """
    now = datetime.now(timezone.utc)
    tenant_ids = [
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT id FROM tenants t WHERE NOT EXISTS "
                "(SELECT 1 FROM categories c WHERE c.tenant_id = t.id)"
            )
        )
    ]
    for tenant_id in tenant_ids:
        id_by_key: dict[str, int] = {}
        for key, name, depth, parent_key in _CATEGORIES:
            parent_id = id_by_key.get(parent_key) if parent_key else None
            result = conn.execute(
                sa.text(
                    "INSERT INTO categories "
                    "(tenant_id, parent_id, name, depth, sort_order, created_at, updated_at) "
                    "VALUES (:tenant_id, :parent_id, :name, :depth, 0, :now, :now) "
                    "RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "parent_id": parent_id,
                    "name": name,
                    "depth": depth,
                    "now": now,
                },
            )
            id_by_key[key] = result.scalar_one()


def upgrade() -> None:
    _backfill(op.get_bind())


def downgrade() -> None:
    # No-op có chủ đích: đây là seed dữ liệu 1 lần, không cần đảo ngược. Xóa nhầm nhóm hàng
    # mà chủ shop có thể đã bắt đầu dùng (gán vào sản phẩm) là rủi ro hơn nhiều so với giữ lại.
    pass
