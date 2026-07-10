# Nhóm hàng mặc định khi đăng ký shop + backfill shop cũ — Design

Ngày: 2026-07-10

## 1. Bối cảnh & mục tiêu

Môi trường test/demo (`scripts/seed_demo.py`) có sẵn danh sách 21 nhóm hàng tạp hóa (2 cấp,
đúng constraint `depth IN (1,2)`) dùng để seed dữ liệu demo. Production hiện tại: shop đăng ký
xong không có nhóm hàng nào — chủ shop phải tự tạo từ đầu.

**Mục tiêu:**
1. Mỗi shop đăng ký mới (`POST /auth/register`) tự động có sẵn 21 nhóm hàng mặc định (giống
   danh sách trong `seed_demo.py`), không cần tự tạo tay.
2. Shop đã đăng ký trước đây trên production (nếu có) mà **chưa có nhóm hàng nào** cũng được
   backfill cùng bộ 21 nhóm hàng này — chạy tự động 1 lần qua Alembic migration, không cần admin
   nhớ chạy tay.

**Ngoài phạm vi (non-goals):**
- Không cho phép tùy biến danh sách nhóm hàng mặc định theo từng shop (dùng chung 1 bộ cố định
  cho mọi shop mới).
- Không tự động seed lại nếu chủ shop tự xóa hết nhóm hàng sau khi đã có — chỉ áp dụng lúc đăng
  ký hoặc lúc migration backfill chạy đúng 1 lần.
- Không đụng vào `scripts/seed_demo.py` hiện có (vẫn là công cụ demo/test riêng, không phụ thuộc
  vào constant mới).
- Không thêm audit log riêng cho việc seed nhóm hàng mặc định (nhất quán với việc `register()`
  hiện tại cũng không audit-log việc tạo tenant/user).

## 2. Danh sách nhóm hàng mặc định

Copy nguyên 21 dòng từ `CATEGORIES` trong `scripts/seed_demo.py` (dạng `(key, name, depth,
parent_key)`, `parent_key = None` nghĩa là depth 1):

```
do_uong,      "Đồ uống",                 1, None
nc_ngot,      "Nước ngọt & Tăng lực",    2, do_uong
bia_ruou,     "Bia & Rượu",              2, do_uong
nc_chai,      "Nước đóng chai & Trà",    2, do_uong
tp_kho,       "Thực phẩm khô",           1, None
mi_bun,       "Mì tôm & Bún khô",        2, tp_kho
gao_bot,      "Gạo & Bột",               2, tp_kho
gia_vi,       "Gia vị & Dầu ăn",         1, None
bk_snack,     "Bánh kẹo & Snack",        1, None
snack_bq,     "Snack & Bánh quy",        2, bk_snack
keo_choco,    "Kẹo & Chocolate",         2, bk_snack
sua,          "Sữa & Sản phẩm sữa",      1, None
sua_tuoi,     "Sữa tươi & Đóng hộp",    2, sua
sua_chua,     "Sữa chua & Phô mai",      2, sua
cs_cn,        "Chăm sóc cá nhân",        1, None
ve_sinh,      "Vệ sinh cá nhân",         2, cs_cn
dau_goi,      "Dầu gội & Dưỡng da",     2, cs_cn
dd_gd,        "Đồ dùng gia đình",        1, None
tay_rua,      "Tẩy rửa",                 2, dd_gd
dung_cu,      "Dụng cụ & Tiện ích",      2, dd_gd
thuoc_la,     "Thuốc lá & Diêm quẹt",   1, None
```

Mọi dòng chèn với `sort_order = 0` (giống `seed_demo.py`).

## 3. Backend — tạo cho shop mới

### 3.1. Constant dùng chung

File mới `backend/shared/default_categories.py`:

```python
DEFAULT_CATEGORIES: list[tuple[str, str, int, str | None]] = [
    ("do_uong", "Đồ uống", 1, None),
    ("nc_ngot", "Nước ngọt & Tăng lực", 2, "do_uong"),
    # ... đủ 21 dòng như mục 2
]
```

### 3.2. Helper tạo nhóm hàng

Hàm mới trong `backend/modules/product/service.py`:

```python
async def create_default_categories_for_tenant(
    db: AsyncSession, tenant_id: int
) -> list[Category]:
    """Seed 21 nhóm hàng mặc định cho 1 tenant. Chèn depth=1 trước, rồi depth=2
    tham chiếu parent_id vừa tạo. KHÔNG tự commit — caller kiểm soát transaction.
    KHÔNG ghi audit log — đây là seed hệ thống, không phải CRUD action của user
    (khác `create_category()` hiện có)."""
    id_by_key: dict[str, int] = {}
    created: list[Category] = []
    for key, name, depth, parent_key in DEFAULT_CATEGORIES:
        parent_id = id_by_key.get(parent_key) if parent_key else None
        cat = Category(
            tenant_id=tenant_id,
            parent_id=parent_id,
            name=name,
            depth=depth,
            sort_order=0,
        )
        db.add(cat)
        await db.flush()
        id_by_key[key] = cat.id
        created.append(cat)
    return created
```

Vì `DEFAULT_CATEGORIES` liệt kê nhóm cha (depth 1) trước nhóm con (depth 2) theo đúng thứ tự,
vòng lặp tuần tự đảm bảo `parent_key` luôn đã có trong `id_by_key` khi cần.

### 3.3. Gọi trong `register()`

`backend/modules/auth/service.py`, sau đoạn tạo tenant hiện có:

```python
db.add(tenant)
await db.flush()
await product_service.create_default_categories_for_tenant(db, tenant.id)
```

(import `backend.modules.product.service as product_service` ở đầu file). Phần còn lại của
`register()` (tạo user, issue token, commit) giữ nguyên — nhóm hàng nằm trong cùng transaction,
nếu có lỗi ở bước sau thì rollback luôn cả nhóm hàng lẫn tenant/user (đúng tính atomic hiện có).

## 4. Backfill shop cũ (Alembic data migration)

File mới `alembic/versions/010_backfill_default_categories.py`. Đây là **data migration** đầu
tiên trong repo (các migration trước chỉ đổi schema) — tự chứa danh sách 21 dòng ngay trong file
migration (KHÔNG import từ `backend/shared/default_categories.py`), vì migration phải ổn định
theo thời gian, độc lập với code app có thể thay đổi sau này.

```python
"""backfill default categories for tenants without any category

Revision ID: 010_backfill_default_categories
Revises: 009_tenant_expiry
Create Date: 2026-07-10 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_backfill_default_categories"
down_revision: Union[str, None] = "009_tenant_expiry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Snapshot cố định tại thời điểm viết migration — KHÔNG import từ backend/shared/.
_CATEGORIES: list[tuple[str, str, int, str | None]] = [
    ("do_uong", "Đồ uống", 1, None),
    # ... đủ 21 dòng như mục 2
]


def _backfill(conn) -> None:
    """Thân logic tách riêng khỏi upgrade() để test gọi trực tiếp được (truyền connection
    của test DB), không cần chạy qua toàn bộ Alembic upgrade chain."""
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
                    "VALUES (:tenant_id, :parent_id, :name, :depth, 0, NOW(), NOW()) "
                    "RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "parent_id": parent_id,
                    "name": name,
                    "depth": depth,
                },
            )
            id_by_key[key] = result.scalar_one()


def upgrade() -> None:
    _backfill(op.get_bind())


def downgrade() -> None:
    # No-op có chủ đích: đây là seed dữ liệu 1 lần, không cần đảo ngược. Xóa nhầm nhóm hàng
    # mà chủ shop có thể đã bắt đầu dùng (gán vào sản phẩm) là rủi ro hơn nhiều so với giữ lại.
    pass
```

Vì `alembic upgrade head` đã chạy tự động trong lệnh khởi động container `api`
(`docker-compose.deploy.yml`), migration này tự áp dụng ngay ở lần deploy tiếp theo — không cần
thao tác tay nào thêm trên VPS. Test gọi thẳng `_backfill(conn)` với connection của DB test
(mục 6), không cần dựng lại toàn bộ chain migration.

## 5. Error handling & edge cases

- Tenant đăng ký **sau khi** migration 010 đã chạy: không bị seed 2 lần — `register()` luôn tạo
  tenant mới (id mới, chưa có category nào), migration 010 chỉ chạy đúng 1 lần lúc `alembic
  upgrade head` (Alembic tự theo dõi qua bảng `alembic_version`, không chạy lại).
- Tenant có sẵn category (tự tạo tay hoặc từ `seed_demo.py`) → migration bỏ qua nhờ điều kiện
  `NOT EXISTS`, không tạo trùng.
- Chủ shop xóa hết nhóm hàng sau khi đã có (kể cả nhóm mặc định) → **không** có cơ chế tự seed
  lại (đúng ngoài phạm vi nêu ở mục 1).
- Lỗi giữa chừng khi tạo nhóm hàng trong `register()` (vd DB lỗi) → rollback toàn bộ transaction
  (tenant, user, category) — không để lại tenant "mồ côi" thiếu nhóm hàng.

## 6. Testing

- `tests/test_auth.py`: test `register()` thành công → query `categories` theo `tenant_id` trả
  về đúng 21 dòng; kiểm tra vài quan hệ cha-con cụ thể (VD nhóm "Nước ngọt & Tăng lực" có
  `parent_id` trỏ đúng tới nhóm "Đồ uống" của cùng tenant, không lẫn tenant khác).
- `tests/test_product.py` (hoặc file mới): test trực tiếp
  `create_default_categories_for_tenant()` — gọi 2 lần trên 2 tenant khác nhau, xác nhận mỗi
  tenant có category riêng (tenant isolation), không lẫn `parent_id` giữa 2 tenant.
- Test cho migration 010: vì đây là raw SQL chạy qua `op.get_bind()`, viết test tích hợp dùng
  DB test hiện có — tạo 1 tenant không category + 1 tenant có sẵn 1 category thủ công, chạy logic
  upgrade (extract phần thân vòng lặp thành hàm thuần nhận `conn`/`session` để gọi trực tiếp từ
  test, tương tự cách `extend_tenant.py` tách hàm `extend_tenant()` khỏi `_main()` CLI) — assert
  tenant thứ nhất có đủ 21 category mới, tenant thứ hai vẫn chỉ có đúng 1 category ban đầu (không
  bị thêm 21 category mới).
