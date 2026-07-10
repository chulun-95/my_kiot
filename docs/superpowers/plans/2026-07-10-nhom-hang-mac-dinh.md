# Nhóm hàng mặc định khi đăng ký shop + backfill shop cũ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mỗi shop đăng ký mới tự động có sẵn 21 nhóm hàng tạp hóa mặc định (2 cấp); shop cũ (nếu có) chưa có nhóm hàng nào cũng được backfill cùng bộ này qua 1 Alembic migration tự chạy khi deploy.

**Architecture:** Danh sách 21 nhóm hàng sống ở 1 hằng số dùng chung (`backend/shared/default_categories.py`) cho code app. Một helper insert thuần (`create_default_categories_for_tenant`) được gọi trong `auth_service.register()` ngay sau khi tạo `Tenant`, trong cùng transaction hiện có (rollback atomic nếu lỗi). Backfill cho tenant cũ nằm trong 1 Alembic data migration độc lập, **tự chứa** bản copy riêng của danh sách 21 nhóm hàng (không import từ code app, vì migration phải ổn định theo thời gian) — chỉ áp dụng cho tenant chưa có category nào.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Alembic, pytest + pytest-asyncio, SQLite in-memory (test DB) / PostgreSQL (production).

## Global Constraints

- Mọi query/insert phải filter/gán đúng `tenant_id` — không có `deleted_at` cần set (categories seed mới, chưa xóa).
- Không thêm audit log cho việc seed nhóm hàng mặc định (nhất quán với `register()` hiện tại không audit-log tạo tenant/user).
- Không đụng `scripts/seed_demo.py` (dùng raw SQL riêng, không gọi qua `register()`, không bị ảnh hưởng).
- Migration `010_backfill_default_categories.py` tự chứa danh sách 21 dòng, KHÔNG import từ `backend/shared/default_categories.py`.
- `downgrade()` của migration 010 là no-op có chủ đích (seed 1 lần, không đảo ngược).
- Test DB là SQLite in-memory (`tests/conftest.py`) — mọi SQL trong migration phải là SQL chuẩn/portable, KHÔNG dùng hàm riêng của Postgres như `NOW()` (SQLite không có). Dùng bind-param truyền timestamp Python thay vì gọi hàm SQL.

---

### Task 1: Hằng số danh sách nhóm hàng mặc định dùng chung

**Files:**
- Create: `backend/shared/default_categories.py`
- Test: `tests/test_default_categories.py`

**Interfaces:**
- Produces: `DEFAULT_CATEGORIES: list[tuple[str, str, int, str | None]]` — mỗi tuple là `(key, name, depth, parent_key)`. Task 2 và Task 3 import và dùng trực tiếp hằng số này.

- [ ] **Step 1: Viết test trước (fail vì module chưa tồn tại)**

Tạo `tests/test_default_categories.py`:

```python
from backend.shared.default_categories import DEFAULT_CATEGORIES


def test_default_categories_has_21_entries():
    assert len(DEFAULT_CATEGORIES) == 21


def test_default_categories_depth_values_valid():
    for key, name, depth, parent_key in DEFAULT_CATEGORIES:
        assert depth in (1, 2)
        assert isinstance(key, str) and key
        assert isinstance(name, str) and name


def test_default_categories_parent_keys_reference_earlier_depth1():
    """Mọi parent_key (nếu có) phải trỏ tới 1 key depth=1 đã xuất hiện TRƯỚC nó trong danh
    sách — đảm bảo vòng lặp insert tuần tự trong Task 2 luôn có parent_id sẵn khi cần."""
    seen_depth1_keys: set[str] = set()
    for key, name, depth, parent_key in DEFAULT_CATEGORIES:
        if parent_key is not None:
            assert parent_key in seen_depth1_keys, (
                f"'{key}' tham chiếu parent_key='{parent_key}' chưa xuất hiện hoặc không phải depth=1"
            )
        if depth == 1:
            seen_depth1_keys.add(key)


def test_default_categories_keys_are_unique():
    keys = [key for key, *_ in DEFAULT_CATEGORIES]
    assert len(keys) == len(set(keys))
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `pytest tests/test_default_categories.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'backend.shared.default_categories'`

- [ ] **Step 3: Tạo file hằng số**

Tạo `backend/shared/default_categories.py`:

```python
"""Danh sách 21 nhóm hàng tạp hóa mặc định (2 cấp), dùng khi:
- Shop mới đăng ký (backend/modules/auth/service.py:register()).
- Backfill shop cũ chưa có nhóm hàng nào (xem alembic/versions/010_backfill_default_categories.py
  — file đó TỰ CHỨA bản copy riêng của danh sách này, KHÔNG import từ đây, vì migration phải
  ổn định theo thời gian, độc lập với thay đổi của code app).

Mỗi tuple: (key, name, depth, parent_key). parent_key=None nghĩa là depth=1 (gốc).
Thứ tự liệt kê quan trọng: mọi depth=1 phải đứng TRƯỚC depth=2 tham chiếu nó, vì vòng lặp
insert tuần tự dựa vào đó để luôn có parent_id sẵn sàng.
"""

DEFAULT_CATEGORIES: list[tuple[str, str, int, str | None]] = [
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
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `pytest tests/test_default_categories.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/shared/default_categories.py tests/test_default_categories.py
git commit -m "feat(product): thêm hằng số 21 nhóm hàng tạp hóa mặc định dùng chung"
```

---

### Task 2: Helper tạo nhóm hàng mặc định cho 1 tenant

**Files:**
- Modify: `backend/modules/product/service.py` (thêm hàm mới cuối phần CATEGORY, sau `delete_category`)
- Test: `tests/test_product.py` (thêm test mới cuối file)

**Interfaces:**
- Consumes: `DEFAULT_CATEGORIES` từ Task 1 (`backend.shared.default_categories`).
- Produces: `async def create_default_categories_for_tenant(db: AsyncSession, tenant_id: int) -> list[Category]` — Task 3 gọi hàm này với `(db, tenant.id)`, không tự commit, không tự ghi audit.

- [ ] **Step 1: Viết test trước (fail vì hàm chưa tồn tại)**

Thêm vào cuối `tests/test_product.py`:

```python
@pytest.mark.asyncio
async def test_create_default_categories_for_tenant(db_session):
    from sqlalchemy import select
    from backend.modules.product.service import create_default_categories_for_tenant
    from backend.modules.product.models import Category
    from backend.modules.tenant.models import Tenant

    tenant = Tenant(name="Shop Default Cat", slug="shop-default-cat", address="1 Đường A")
    db_session.add(tenant)
    await db_session.flush()

    created = await create_default_categories_for_tenant(db_session, tenant.id)
    await db_session.commit()

    assert len(created) == 21

    rows = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant.id))
    ).scalars().all()
    assert len(rows) == 21

    by_name = {c.name: c for c in rows}
    do_uong = by_name["Đồ uống"]
    assert do_uong.depth == 1
    assert do_uong.parent_id is None
    nc_ngot = by_name["Nước ngọt & Tăng lực"]
    assert nc_ngot.depth == 2
    assert nc_ngot.parent_id == do_uong.id


@pytest.mark.asyncio
async def test_create_default_categories_tenant_isolation(db_session):
    from sqlalchemy import select
    from backend.modules.product.service import create_default_categories_for_tenant
    from backend.modules.product.models import Category
    from backend.modules.tenant.models import Tenant

    tenant_a = Tenant(name="Shop A", slug="shop-a-cat", address="1 Đường A")
    tenant_b = Tenant(name="Shop B", slug="shop-b-cat", address="2 Đường B")
    db_session.add_all([tenant_a, tenant_b])
    await db_session.flush()

    await create_default_categories_for_tenant(db_session, tenant_a.id)
    await create_default_categories_for_tenant(db_session, tenant_b.id)
    await db_session.commit()

    rows_a = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant_a.id))
    ).scalars().all()
    rows_b = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant_b.id))
    ).scalars().all()
    assert len(rows_a) == 21
    assert len(rows_b) == 21

    ids_a = {c.id for c in rows_a}
    ids_b = {c.id for c in rows_b}
    assert ids_a.isdisjoint(ids_b)

    # parent_id của mỗi tenant chỉ trỏ vào category CÙNG tenant
    for c in rows_a:
        if c.parent_id is not None:
            assert c.parent_id in ids_a
    for c in rows_b:
        if c.parent_id is not None:
            assert c.parent_id in ids_b
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `pytest tests/test_product.py -v -k default_categories`
Expected: FAIL với `ImportError: cannot import name 'create_default_categories_for_tenant'`

- [ ] **Step 3: Thêm import và hàm mới vào `backend/modules/product/service.py`**

Sửa khối import ở đầu file (dòng 20-23 hiện tại):

```python
from backend.shared import audit as audit_helper
from backend.shared.code_generator import generate_code
from backend.shared.default_categories import DEFAULT_CATEGORIES
from backend.shared.pagination import paginate
from backend.shared.text import vi_like_pattern
```

Thêm hàm mới ngay sau hàm `delete_category` hiện có (cuối phần `# CATEGORY`):

```python
async def create_default_categories_for_tenant(
    db: AsyncSession, tenant_id: int
) -> list[Category]:
    """Seed 21 nhóm hàng tạp hóa mặc định cho 1 tenant mới (gọi từ auth_service.register()
    hoặc migration backfill). Chèn depth=1 trước, rồi depth=2 tham chiếu parent_id vừa tạo —
    DEFAULT_CATEGORIES đã đảm bảo thứ tự này. KHÔNG tự commit (caller kiểm soát transaction).
    KHÔNG ghi audit log (đây là seed hệ thống, khác create_category() là CRUD action của user)."""
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

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `pytest tests/test_product.py -v -k default_categories`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/modules/product/service.py tests/test_product.py
git commit -m "feat(product): thêm create_default_categories_for_tenant()"
```

---

### Task 3: Gọi seed nhóm hàng mặc định khi đăng ký shop mới

**Files:**
- Modify: `backend/modules/auth/service.py:31,79-86` (thêm import + gọi helper)
- Modify: `tests/test_category.py:71-94` (sửa test bị ảnh hưởng bởi nhóm hàng mặc định mới)
- Test: `tests/test_auth.py` (thêm test mới cuối phần Register)

**Interfaces:**
- Consumes: `create_default_categories_for_tenant(db, tenant_id)` từ Task 2.

**⚠️ Tác động tới test hiện có:** `registered_owner` fixture (dùng bởi rất nhiều test file: `test_category.py`, `test_product.py`, `test_inventory.py`, `test_sales.py`, `test_report.py`, `test_customer.py`...) gọi thẳng `POST /auth/register` — sau task này, MỌI tenant tạo qua fixture đó sẽ có sẵn 21 category. Đã rà soát toàn bộ `tests/*.py`: chỉ có **1 test** phá vỡ giả định "tenant mới có 0 category" — `test_list_categories_returns_tree` trong `tests/test_category.py:71-94` (assert `len(items) == 1` và lấy `items[0]` làm gốc vừa tạo). Các test khác trong `test_category.py`/`test_product.py` chỉ kiểm tra sự hiện diện/vắng mặt của ID cụ thể (không đếm tổng số), không bị ảnh hưởng.

- [ ] **Step 1: Viết test trước cho hành vi mới (fail vì chưa wire)**

Thêm vào cuối phần "Register" trong `tests/test_auth.py` (sau `test_register_slug_collision_gets_suffix`):

```python
@pytest.mark.asyncio
async def test_register_creates_default_categories(client):
    payload = {
        "shop_name": "Tap Hoa Default Categories",
        "phone": "0905555555",
        "address": "1 Đường Y, Quận 1",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    access_token = resp.json()["access_token"]

    cat_resp = await client.get(
        "/api/v1/categories", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert cat_resp.status_code == 200
    items = cat_resp.json()["items"]

    def _count(nodes):
        return sum(1 + _count(n["children"]) for n in nodes)

    assert _count(items) == 21

    do_uong = next(n for n in items if n["name"] == "Đồ uống")
    child_names = {c["name"] for c in do_uong["children"]}
    assert "Nước ngọt & Tăng lực" in child_names
    assert "Bia & Rượu" in child_names
    assert "Nước đóng chai & Trà" in child_names
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `pytest tests/test_auth.py -v -k test_register_creates_default_categories`
Expected: FAIL — `_count(items) == 21` thất bại vì hiện `items` rỗng (chưa wire helper vào `register()`)

- [ ] **Step 3: Wire helper vào `register()`**

Sửa import trong `backend/modules/auth/service.py` — thêm 1 dòng mới TRƯỚC `from backend.modules.tenant.models import Tenant` (dòng 31 hiện tại), giữ thứ tự alphabet theo `modules.*` đã có:

```python
from backend.modules.product import service as product_service
from backend.modules.tenant.models import Tenant
```

Sửa hàm `register()` — thêm 1 dòng ngay sau `await db.flush()` của đoạn tạo tenant (dòng 85-86 hiện tại):

```python
    tenant = Tenant(
        name=payload.shop_name.strip(),
        slug=slug,
        address=payload.address.strip(),
        expires_at=add_months(datetime.now(tz=timezone.utc), 6),
    )
    db.add(tenant)
    await db.flush()
    await product_service.create_default_categories_for_tenant(db, tenant.id)

    user = User(
```

- [ ] **Step 4: Chạy test mới, xác nhận pass**

Run: `pytest tests/test_auth.py -v -k test_register_creates_default_categories`
Expected: 1 passed

- [ ] **Step 5: Chạy toàn bộ test suite, xác nhận test nào vỡ**

Run: `pytest tests/ -v`
Expected: FAIL đúng 1 test — `tests/test_category.py::test_list_categories_returns_tree` (assert `len(body["items"]) == 1` sai vì giờ có thêm 8 category gốc mặc định + 1 category "Đồ uống" tự tạo trong test = 9 items gốc)

- [ ] **Step 6: Sửa test bị ảnh hưởng — tìm theo ID thay vì đếm tổng/lấy index 0**

Sửa `tests/test_category.py:71-94`, thay toàn bộ hàm `test_list_categories_returns_tree`:

```python
@pytest.mark.asyncio
async def test_list_categories_returns_tree(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/categories", json={"name": "Đồ uống Riêng"}, headers=h
    )).json()
    await client.post(
        "/api/v1/categories",
        json={"name": "Nước ngọt", "parent_id": p["id"]},
        headers=h,
    )
    await client.post(
        "/api/v1/categories",
        json={"name": "Cà phê", "parent_id": p["id"]},
        headers=h,
    )

    r = await client.get("/api/v1/categories", headers=h)
    assert r.status_code == 200
    body = r.json()
    root = next(n for n in body["items"] if n["id"] == p["id"])
    assert root["name"] == "Đồ uống Riêng"
    assert len(root["children"]) == 2
    child_names = {c["name"] for c in root["children"]}
    assert child_names == {"Nước ngọt", "Cà phê"}
```

(Đổi tên `"Đồ uống"` → `"Đồ uống Riêng"` để tránh trùng tên với nhóm hàng mặc định — chỉ để dễ đọc test, không bắt buộc vì tìm theo `id` đã đủ chính xác.)

- [ ] **Step 7: Chạy lại toàn bộ test suite, xác nhận tất cả pass**

Run: `pytest tests/ -v`
Expected: tất cả pass (0 failed)

- [ ] **Step 8: Commit**

```bash
git add backend/modules/auth/service.py tests/test_auth.py tests/test_category.py
git commit -m "feat(auth): tự động tạo 21 nhóm hàng mặc định khi đăng ký shop mới"
```

---

### Task 4: Backfill nhóm hàng mặc định cho tenant cũ (Alembic migration)

**Files:**
- Create: `alembic/versions/010_backfill_default_categories.py`
- Test: `tests/test_backfill_default_categories.py`

**Interfaces:**
- Consumes: không phụ thuộc code Task 1-3 (tự chứa danh sách riêng theo Global Constraints).
- Produces: hàm thuần `_backfill(conn)` trong module migration — test import trực tiếp qua `importlib` (tên file bắt đầu bằng số, không thể `import` bằng cú pháp thường).

- [ ] **Step 1: Viết test trước (fail vì migration chưa tồn tại)**

Tạo `tests/test_backfill_default_categories.py`:

```python
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.modules.product.models import Category
from backend.modules.tenant.models import Tenant

MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic" / "versions" / "010_backfill_default_categories.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "migration_010_backfill_default_categories", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_backfill_seeds_tenant_without_any_category(db_session):
    migration = _load_migration()

    tenant = Tenant(name="Shop Cu Chua Co Cat", slug="shop-cu-chua-co-cat", address="1 A")
    db_session.add(tenant)
    await db_session.flush()

    def _run(sync_session):
        conn = sync_session.connection()
        migration._backfill(conn)

    await db_session.run_sync(_run)
    await db_session.commit()

    rows = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant.id))
    ).scalars().all()
    assert len(rows) == 21

    by_name = {c.name: c for c in rows}
    assert by_name["Đồ uống"].depth == 1
    assert by_name["Nước ngọt & Tăng lực"].parent_id == by_name["Đồ uống"].id


@pytest.mark.asyncio
async def test_backfill_skips_tenant_with_existing_category(db_session):
    migration = _load_migration()

    tenant = Tenant(name="Shop Da Co Cat", slug="shop-da-co-cat", address="2 B")
    db_session.add(tenant)
    await db_session.flush()
    existing = Category(tenant_id=tenant.id, name="Tự Tạo", depth=1, sort_order=0)
    db_session.add(existing)
    await db_session.flush()

    def _run(sync_session):
        conn = sync_session.connection()
        migration._backfill(conn)

    await db_session.run_sync(_run)
    await db_session.commit()

    rows = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant.id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "Tự Tạo"


@pytest.mark.asyncio
async def test_backfill_isolates_between_tenants(db_session):
    migration = _load_migration()

    tenant_a = Tenant(name="Shop Old A", slug="shop-old-a", address="3 C")
    tenant_b = Tenant(name="Shop Old B", slug="shop-old-b", address="4 D")
    db_session.add_all([tenant_a, tenant_b])
    await db_session.flush()

    def _run(sync_session):
        conn = sync_session.connection()
        migration._backfill(conn)

    await db_session.run_sync(_run)
    await db_session.commit()

    rows_a = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant_a.id))
    ).scalars().all()
    rows_b = (
        await db_session.execute(select(Category).where(Category.tenant_id == tenant_b.id))
    ).scalars().all()
    assert len(rows_a) == 21
    assert len(rows_b) == 21
    ids_a = {c.id for c in rows_a}
    ids_b = {c.id for c in rows_b}
    assert ids_a.isdisjoint(ids_b)
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `pytest tests/test_backfill_default_categories.py -v`
Expected: FAIL — `FileNotFoundError` (migration file chưa tồn tại)

- [ ] **Step 3: Tạo migration**

Tạo `alembic/versions/010_backfill_default_categories.py`:

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `pytest tests/test_backfill_default_categories.py -v`
Expected: 3 passed

- [ ] **Step 5: Verify migration áp dụng được trên Postgres thật (không chỉ SQLite test)**

Run (cần Postgres cục bộ hoặc container tạm — dùng `DATABASE_URL` đang cấu hình cho dev):
```bash
alembic upgrade head
```
Expected: chạy xong không lỗi, log hiện `010_backfill_default_categories` là revision mới nhất. Nếu không có Postgres cục bộ sẵn sàng, bỏ qua bước này và ghi chú lại — migration sẽ được verify thực tế ở lần deploy tiếp theo (staging/production).

- [ ] **Step 6: Chạy toàn bộ test suite lần cuối**

Run: `pytest tests/ -v`
Expected: tất cả pass (0 failed)

- [ ] **Step 7: Commit**

```bash
git add alembic/versions/010_backfill_default_categories.py tests/test_backfill_default_categories.py
git commit -m "feat(product): backfill nhóm hàng mặc định cho tenant cũ chưa có nhóm hàng nào"
```
