# Bán hàng offline Android — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép bán hàng + thanh toán (tiền mặt/CK, khách vãng lai) khi mất mạng trên app Android; đơn lưu local rồi tự đồng bộ lên server khi có mạng, idempotent, cho phép âm tồn.

**Architecture:** Local-first. Android có Room (catalog cache + outbox đơn hàng). POS đọc SP/barcode từ cache, checkout ghi đơn `OFFLINE_SALE(PENDING)` rồi in bill mã tạm. `SyncManager` đẩy batch lên `POST /invoices/offline-sync` (idempotent theo `client_uuid`), server tạo Invoice `COMPLETED`, sinh mã HD thật theo ngày bán, trừ tồn (cho âm), ghi sổ quỹ.

**Tech Stack:** Backend FastAPI + SQLAlchemy 2.0 async + Alembic + PostgreSQL. Android Kotlin + Jetpack Compose + Hilt + Retrofit + Room + kotlinx.serialization. Test: pytest (BE), JUnit4 + mockk + turbine + coroutines-test (AND).

## Global Constraints

- Mọi query backend filter `tenant_id` lấy từ JWT (`current_user.tenant_id`) — không bao giờ từ request.
- Tiền tệ dùng `DECIMAL(15,2)` / `Numeric(15,2)`; trên Android & DTO truyền **Decimal dạng String** để tránh sai số float.
- Mọi thông báo lỗi/validation/UI hiển thị cho người dùng PHẢI bằng **tiếng Việt**; `error.code` giữ UPPER_SNAKE_CASE tiếng Anh.
- App Android hiển thị lỗi bằng **ErrorDialog dùng chung** (`core/ui/ErrorDialog.kt`), KHÔNG dùng toast/snackbar.
- Tồn kho = append-only `stock_movements`; bảng `inventory` chỉ là cache. Mọi thay đổi tồn phải ghi 1 `StockMovement` + cập nhật `inventory.quantity`.
- Idempotency offline-sync: khóa `UNIQUE(tenant_id, client_uuid)` — đẩy lại cùng đơn không được nhân đôi.
- Migration mới: revision `009_offline_sales`, `down_revision = "008_receipt_payment_method"`, file `alembic/versions/009_offline_sales.py`.
- Backend mutation phải ghi `audit_logs` qua `backend.shared.audit`; commit do caller quyết định.
- Phạm vi offline: chỉ CASH/BANK_TRANSFER, khách vãng lai (`customer_id=NULL`). KHÔNG bán nợ, KHÔNG gán khách, KHÔNG nhập kho offline.

---

## File Structure

**Backend (mới/sửa):**
- `backend/modules/sales/models.py` — *Modify*: thêm cột `client_uuid, origin, offline_temp_code, device_id` vào `Invoice`.
- `alembic/versions/009_offline_sales.py` — *Create*: migration cột + unique index.
- `backend/shared/code_generator.py` — *Modify*: `generate_code(..., when: datetime | None)`.
- `backend/modules/product/schemas.py` — *Modify*: thêm `CatalogProductDto`, `CatalogResponse`.
- `backend/modules/product/service.py` — *Modify*: `get_catalog(...)`.
- `backend/modules/product/router.py` — *Modify*: `GET /products/catalog`.
- `backend/modules/sales/schemas.py` — *Modify*: thêm `OfflineSaleItemDto`, `OfflineSaleDto`, `OfflineSyncRequest`, `OfflineSyncResultDto`, `OfflineSyncResponse`.
- `backend/modules/sales/offline_service.py` — *Create*: `sync_offline_sales(...)`.
- `backend/modules/sales/router.py` — *Modify*: `POST /invoices/offline-sync`.
- `backend/modules/report/service.py` + `router.py` — *Modify*: `GET /reports/offline-negative`.
- `tests/test_offline_sales.py` — *Create*.

**Android (mới/sửa):**
- `android/gradle/libs.versions.toml` + `android/app/build.gradle.kts` — *Modify*: thêm Room.
- `core/offline/db/OfflineDb.kt`, `entities/*.kt`, `dao/*.kt` — *Create*: Room.
- `core/offline/OfflineModule.kt` — *Create*: Hilt provides DB + DAOs.
- `core/network/CatalogApi.kt`, `OfflineSyncApi.kt` + `dto/CatalogDtos.kt`, `dto/OfflineSyncDtos.kt` — *Create*.
- `core/offline/CatalogCache.kt` — *Create*.
- `core/offline/OfflineSaleRepository.kt` — *Create*.
- `core/offline/SyncManager.kt` — *Create*.
- `core/offline/DeviceId.kt` — *Create*.
- `feature/pos/data/PosRepository.kt`, `PosViewModel.kt` — *Modify*: local-first.
- `feature/pos/PosScreen.kt` + `core/ui` — *Modify*: thanh trạng thái sync.
- `feature/offline/UnsyncedSalesScreen.kt` + `UnsyncedSalesViewModel.kt` — *Create*.
- Test: `core/offline/SyncManagerTest.kt`, `OfflineSaleRepositoryTest.kt`, `CatalogCacheTest.kt`.

---

## TASK BE-1: Migration + model cột offline trên `invoices`

**Files:**
- Modify: `backend/modules/sales/models.py` (class `Invoice`, sau dòng `created_by`, ~line 85-87)
- Create: `alembic/versions/009_offline_sales.py`
- Modify: `backend/shared/code_generator.py` (hàm `generate_code`)
- Test: `tests/test_offline_sales.py`

**Interfaces:**
- Produces: `Invoice.client_uuid: Optional[str]`, `Invoice.origin: str`, `Invoice.offline_temp_code: Optional[str]`, `Invoice.device_id: Optional[str]`.
- Produces: `generate_code(db, tenant_id, prefix, with_date=True, when: datetime | None = None) -> str`.

- [ ] **Step 1: Viết test migration/model (idempotency unique + generate_code theo ngày)**

Thêm vào `tests/test_offline_sales.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from backend.shared.code_generator import generate_code


@pytest.mark.asyncio
async def test_generate_code_uses_given_date(db_session, registered_owner):
    tenant_id = registered_owner["tenant"]["id"]
    past = datetime(2026, 1, 5, tzinfo=timezone(timedelta(hours=7)))
    code = await generate_code(db_session, tenant_id, "HD", with_date=True, when=past)
    assert code.startswith("HD20260105-"), code
```

> `db_session` fixture: kiểm `tests/conftest.py`. Nếu tên khác (vd `session`), dùng đúng tên đó.

- [ ] **Step 2: Chạy test → FAIL**

Run: `cd c:/Users/VuongNV/Downloads/my_kiot && python -m pytest tests/test_offline_sales.py -v`
Expected: FAIL — `generate_code() got an unexpected keyword argument 'when'`.

- [ ] **Step 3: Sửa `generate_code` nhận `when`**

Trong `backend/shared/code_generator.py`, đổi chữ ký + dòng `date_part`:
```python
async def generate_code(
    db: AsyncSession,
    tenant_id: int,
    prefix: str,
    with_date: bool = True,
    when: datetime | None = None,
) -> str:
    """Sinh mã `{prefix}{date}-{NNN}` (with_date) hoặc `{prefix}{NNNNNN}`.

    `when` (nếu có) dùng để chọn date_part — phục vụ đơn offline sinh mã theo
    NGÀY BÁN thực, không phải ngày sync. `when` quy về giờ VN trước khi format.
    """
    if with_date:
        ref = (when.astimezone(VN_TZ) if when is not None else datetime.now(tz=VN_TZ))
        date_part = ref.strftime("%Y%m%d")
    else:
        date_part = ""
```
(Phần thân còn lại giữ nguyên. Thêm `from datetime import datetime` đã có sẵn ở đầu file.)

- [ ] **Step 4: Thêm cột vào model `Invoice`**

Trong `backend/modules/sales/models.py`, ngay sau `created_by` (trước block `items: Mapped[...]`), thêm:
```python
    # ----- Offline sales -----
    client_uuid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    origin: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ONLINE", server_default="ONLINE"
    )
    offline_temp_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
```
Và thêm vào `__table_args__` (tuple) một Index unique partial:
```python
        Index(
            "uq_invoices_tenant_client_uuid",
            "tenant_id",
            "client_uuid",
            unique=True,
            postgresql_where=text("client_uuid IS NOT NULL"),
            sqlite_where=text("client_uuid IS NOT NULL"),
        ),
```
Thêm import `text`: dòng `from sqlalchemy import (... text ...)` — bổ sung `text` vào danh sách import.

- [ ] **Step 5: Tạo migration `009_offline_sales.py`**

```python
"""offline sales: client_uuid, origin, temp_code, device_id on invoices

Revision ID: 009_offline_sales
Revises: 008_receipt_payment_method
Create Date: 2026-06-21 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_offline_sales"
down_revision: Union[str, None] = "008_receipt_payment_method"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("client_uuid", sa.String(length=36), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("origin", sa.String(length=10), server_default="ONLINE", nullable=False),
    )
    op.add_column("invoices", sa.Column("offline_temp_code", sa.String(length=30), nullable=True))
    op.add_column("invoices", sa.Column("device_id", sa.String(length=64), nullable=True))
    op.create_index(
        "uq_invoices_tenant_client_uuid",
        "invoices",
        ["tenant_id", "client_uuid"],
        unique=True,
        postgresql_where=sa.text("client_uuid IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_invoices_tenant_client_uuid", table_name="invoices")
    op.drop_column("invoices", "device_id")
    op.drop_column("invoices", "offline_temp_code")
    op.drop_column("invoices", "origin")
    op.drop_column("invoices", "client_uuid")
```

- [ ] **Step 6: Chạy test → PASS**

Run: `python -m pytest tests/test_offline_sales.py::test_generate_code_uses_given_date -v`
Expected: PASS.
(Test suite dùng SQLite in-memory tạo bảng từ models — không chạy alembic; nên cột model mới phải khớp. Nếu conftest chạy `create_all`, model đủ.)

- [ ] **Step 7: Commit**

```bash
git add backend/modules/sales/models.py backend/shared/code_generator.py alembic/versions/009_offline_sales.py tests/test_offline_sales.py
git commit -m "feat(offline): invoices offline columns + generate_code(when)"
```

---

## TASK BE-2: `GET /products/catalog` (full + delta `since`)

**Files:**
- Modify: `backend/modules/product/schemas.py`
- Modify: `backend/modules/product/service.py`
- Modify: `backend/modules/product/router.py`
- Test: `tests/test_offline_sales.py`

**Interfaces:**
- Produces endpoint `GET /api/v1/products/catalog?since=<ISO8601>` → `CatalogResponse`.
- Produces `CatalogResponse { server_time: str, items: list[CatalogProductDto], deleted_ids: list[int] }`.
- `CatalogProductDto { id, sku, barcode?, name, unit, sale_price(str), status, units: list[CatalogUnitDto] }`.
- `CatalogUnitDto { id, unit_name, conversion_rate(str), sale_price(str|null), barcode? }`.

- [ ] **Step 1: Viết test**

```python
@pytest.mark.asyncio
async def test_catalog_returns_active_products_with_units(client, shop):
    h = shop["headers"]
    r = await client.get("/api/v1/products/catalog", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "server_time" in body
    skus = {p["sku"] for p in body["items"]}
    assert {"COC-330", "PEP-1500"} <= skus
    p = next(p for p in body["items"] if p["sku"] == "COC-330")
    assert p["sale_price"] == "12000.00"
    assert "cost_price" not in p          # giá vốn KHÔNG lộ ra catalog
    assert isinstance(p["units"], list)


@pytest.mark.asyncio
async def test_catalog_tenant_isolation(client, shop, registered_owner_b):
    """Tenant B không thấy SP của tenant A."""
    hb = _auth(registered_owner_b["access_token"])
    r = await client.get("/api/v1/products/catalog", headers=hb)
    assert r.status_code == 200
    assert all(p["sku"] not in {"COC-330", "PEP-1500"} for p in r.json()["items"])
```

> Nếu chưa có fixture `registered_owner_b`, tạo trong test này bằng cách đăng ký shop thứ 2 (xem `tests/test_product.py` cho mẫu đăng ký). Nếu khó, tách isolation test sau nhưng vẫn phải có.

- [ ] **Step 2: Chạy test → FAIL**

Run: `python -m pytest tests/test_offline_sales.py -k catalog -v`
Expected: FAIL — 404 Not Found (route chưa có).

- [ ] **Step 3: Thêm schemas**

Trong `backend/modules/product/schemas.py` (cuối file):
```python
class CatalogUnitDto(BaseModel):
    id: int
    unit_name: str
    conversion_rate: str
    sale_price: str | None = None
    barcode: str | None = None


class CatalogProductDto(BaseModel):
    id: int
    sku: str
    barcode: str | None = None
    name: str
    unit: str
    sale_price: str
    status: str
    units: list[CatalogUnitDto] = []


class CatalogResponse(BaseModel):
    server_time: str
    items: list[CatalogProductDto] = []
    deleted_ids: list[int] = []
```
(Dùng đúng base class Pydantic mà file đang dùng — `BaseModel` từ pydantic.)

- [ ] **Step 4: Thêm service `get_catalog`**

Trong `backend/modules/product/service.py`:
```python
from datetime import datetime, timezone
from backend.modules.product.models import Product, ProductUnit
from backend.modules.product.schemas import (
    CatalogProductDto, CatalogUnitDto, CatalogResponse,
)


async def get_catalog(
    db, tenant_id: int, since: datetime | None = None
) -> CatalogResponse:
    now = datetime.now(tz=timezone.utc)

    prod_stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.deleted_at.is_(None),
        Product.status == "ACTIVE",
    )
    if since is not None:
        prod_stmt = prod_stmt.where(Product.updated_at > since)
    products = (await db.execute(prod_stmt)).scalars().all()

    pids = [p.id for p in products]
    units_by_pid: dict[int, list[ProductUnit]] = {}
    if pids:
        units = (await db.execute(
            select(ProductUnit).where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.product_id.in_(pids),
            )
        )).scalars().all()
        for u in units:
            units_by_pid.setdefault(u.product_id, []).append(u)

    items = [
        CatalogProductDto(
            id=p.id, sku=p.sku, barcode=p.barcode, name=p.name,
            unit=p.unit or "cái", sale_price=f"{p.sale_price:.2f}", status=p.status,
            units=[
                CatalogUnitDto(
                    id=u.id, unit_name=u.unit_name,
                    conversion_rate=f"{u.conversion_rate:f}".rstrip("0").rstrip("."),
                    sale_price=(f"{u.sale_price:.2f}" if u.sale_price is not None else None),
                    barcode=u.barcode,
                ) for u in units_by_pid.get(p.id, [])
            ],
        ) for p in products
    ]

    deleted_ids: list[int] = []
    if since is not None:
        deleted = (await db.execute(
            select(Product.id).where(
                Product.tenant_id == tenant_id,
                Product.updated_at > since,
                or_(Product.deleted_at.is_not(None), Product.status != "ACTIVE"),
            )
        )).scalars().all()
        deleted_ids = list(deleted)

    return CatalogResponse(
        server_time=now.isoformat(), items=items, deleted_ids=deleted_ids
    )
```
Thêm import `from sqlalchemy import or_` nếu chưa có ở file.

- [ ] **Step 5: Thêm route**

Trong `backend/modules/product/router.py` (đặt TRƯỚC route `/{id}` để tránh `catalog` bị bắt như id; kiểm thứ tự khai báo):
```python
from datetime import datetime
from backend.modules.product.schemas import CatalogResponse

@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog(
    since: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    since_dt = None
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    return await service.get_catalog(db, current_user.tenant_id, since_dt)
```
(Khớp tên `service`, `get_db`, `get_current_user` như các route khác trong file.)

- [ ] **Step 6: Chạy test → PASS**

Run: `python -m pytest tests/test_offline_sales.py -k catalog -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/modules/product/
git commit -m "feat(offline): GET /products/catalog cho cache offline"
```

---

## TASK BE-3: `POST /invoices/offline-sync` (idempotent, cho âm tồn, sổ quỹ)

**Files:**
- Modify: `backend/modules/sales/schemas.py`
- Create: `backend/modules/sales/offline_service.py`
- Modify: `backend/modules/sales/router.py`
- Test: `tests/test_offline_sales.py`

**Interfaces:**
- Consumes: `generate_code(when=)` (BE-1); helpers từ `sales/service.py`: `_validate_products`, `_lock_inventory_rows`, `_compute_line`, `_get_product_unit_if_given`; `cash_service.record_cash_entry`.
- Produces endpoint `POST /api/v1/invoices/offline-sync` → `OfflineSyncResponse`.
- Produces `OfflineSyncResultDto { client_uuid, status, invoice_id?, code?, caused_negative?, error_code?, error_message? }`.

- [ ] **Step 1: Viết test (bán đứt + idempotent + âm tồn)**

```python
def _sale(client_uuid, p1_id, qty="2", price="12000"):
    return {
        "client_uuid": client_uuid,
        "temp_code": f"TM-dev1-{client_uuid[:6]}",
        "sold_at": "2026-06-21T02:15:30Z",
        "discount_amount": "0",
        "items": [{"product_id": p1_id, "unit_id": None, "quantity": qty,
                   "unit_price": price, "discount_amount": "0"}],
        "payments": [{"method": "CASH", "amount": str(int(float(price) * float(qty)))}],
    }


@pytest.mark.asyncio
async def test_offline_sync_creates_completed_invoice(client, shop):
    h = shop["headers"]
    body = {"device_id": "dev1", "sales": [_sale("uuid-aaaa-0001", shop["p1"]["id"])]}
    r = await client.post("/api/v1/invoices/offline-sync", json=body, headers=h)
    assert r.status_code == 200, r.text
    res = r.json()["results"][0]
    assert res["status"] == "SYNCED"
    assert res["code"].startswith("HD20260621-")
    inv = (await client.get(f"/api/v1/invoices/{res['invoice_id']}", headers=h)).json()
    assert inv["status"] == "COMPLETED"
    assert inv["customer_id"] is None


@pytest.mark.asyncio
async def test_offline_sync_is_idempotent(client, shop):
    h = shop["headers"]
    body = {"device_id": "dev1", "sales": [_sale("uuid-bbbb-0002", shop["p1"]["id"])]}
    r1 = await client.post("/api/v1/invoices/offline-sync", json=body, headers=h)
    r2 = await client.post("/api/v1/invoices/offline-sync", json=body, headers=h)
    id1 = r1.json()["results"][0]["invoice_id"]
    id2 = r2.json()["results"][0]["invoice_id"]
    assert id1 == id2  # không nhân đôi


@pytest.mark.asyncio
async def test_offline_sync_allows_negative_stock(client, shop):
    h = shop["headers"]
    # p1 tồn 100 → bán 250 offline (vượt tồn) phải vẫn SYNCED, caused_negative=True
    body = {"device_id": "dev1", "sales": [_sale("uuid-cccc-0003", shop["p1"]["id"], qty="250")]}
    r = await client.post("/api/v1/invoices/offline-sync", json=body, headers=h)
    res = r.json()["results"][0]
    assert res["status"] == "SYNCED"
    assert res["caused_negative"] is True


@pytest.mark.asyncio
async def test_offline_sync_unknown_product_fails_only_that_sale(client, shop):
    h = shop["headers"]
    bad = _sale("uuid-dddd-0004", 999999)
    good = _sale("uuid-eeee-0005", shop["p1"]["id"])
    r = await client.post("/api/v1/invoices/offline-sync",
                          json={"device_id": "dev1", "sales": [bad, good]}, headers=h)
    results = {x["client_uuid"]: x for x in r.json()["results"]}
    assert results["uuid-dddd-0004"]["status"] == "FAILED"
    assert results["uuid-dddd-0004"]["error_code"] == "PRODUCT_NOT_FOUND"
    assert results["uuid-eeee-0005"]["status"] == "SYNCED"
```

- [ ] **Step 2: Chạy test → FAIL**

Run: `python -m pytest tests/test_offline_sales.py -k offline_sync -v`
Expected: FAIL — 404 (route chưa có).

- [ ] **Step 3: Thêm schemas offline-sync**

Trong `backend/modules/sales/schemas.py`:
```python
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


class OfflineSaleItemDto(BaseModel):
    product_id: int
    unit_id: int | None = None
    quantity: Decimal
    unit_price: Decimal | None = None
    discount_amount: Decimal = Decimal("0")


class OfflinePaymentDto(BaseModel):
    method: str
    amount: Decimal
    note: str | None = None


class OfflineSaleDto(BaseModel):
    client_uuid: str
    temp_code: str
    sold_at: datetime
    discount_amount: Decimal = Decimal("0")
    items: list[OfflineSaleItemDto]
    payments: list[OfflinePaymentDto] = []


class OfflineSyncRequest(BaseModel):
    device_id: str | None = None
    sales: list[OfflineSaleDto]


class OfflineSyncResultDto(BaseModel):
    client_uuid: str
    status: str  # SYNCED | FAILED
    invoice_id: int | None = None
    code: str | None = None
    caused_negative: bool | None = None
    error_code: str | None = None
    error_message: str | None = None


class OfflineSyncResponse(BaseModel):
    results: list[OfflineSyncResultDto] = []
```

- [ ] **Step 4: Tạo `offline_service.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import AppError
from backend.modules.inventory.models import StockMovement
from backend.modules.sales.models import Invoice, InvoiceItem, Payment
from backend.modules.sales.schemas import (
    OfflineSyncRequest, OfflineSyncResponse, OfflineSyncResultDto, OfflineSaleDto,
)
from backend.modules.sales import service as sales_service
from backend.modules.cashbook import service as cash_service
from backend.shared import audit as audit_helper
from backend.shared.code_generator import generate_code


async def _sync_one(
    db: AsyncSession, tenant_id: int, user_id: int, device_id: str | None, sale: OfflineSaleDto
) -> OfflineSyncResultDto:
    # 1. Idempotency
    existing = await db.scalar(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id, Invoice.client_uuid == sale.client_uuid
        )
    )
    if existing is not None:
        return OfflineSyncResultDto(
            client_uuid=sale.client_uuid, status="SYNCED",
            invoice_id=existing.id, code=existing.code,
            caused_negative=False,
        )

    # 2. Validate SP
    product_ids = list({it.product_id for it in sale.items})
    products = await sales_service._validate_products(db, tenant_id, product_ids)

    # 3. Mã HD theo ngày bán
    code = await generate_code(db, tenant_id, "HD", with_date=True, when=sale.sold_at)

    invoice = Invoice(
        tenant_id=tenant_id, code=code, customer_id=None,
        cashier_id=user_id, created_by=user_id, status="COMPLETED",
        discount_amount=sale.discount_amount,
        origin="OFFLINE", client_uuid=sale.client_uuid,
        offline_temp_code=sale.temp_code, device_id=device_id,
        completed_at=sale.sold_at, created_at=sale.sold_at,
    )

    subtotal = Decimal("0")
    cost_total = Decimal("0")
    base_qty_needed: dict[int, Decimal] = {}
    for it in sale.items:
        p = products[it.product_id]
        unit = await sales_service._get_product_unit_if_given(db, tenant_id, p.id, it.unit_id)
        unit_price, line_total = sales_service._compute_line(it, p, unit)
        rate = unit.conversion_rate if unit else Decimal("1")
        base_qty = (it.quantity * rate).quantize(Decimal("0.001"))
        base_qty_needed[p.id] = base_qty_needed.get(p.id, Decimal("0")) + base_qty
        cost_total += (p.cost_price * base_qty).quantize(Decimal("0.01"))
        invoice.items.append(InvoiceItem(
            product_id=p.id, product_name=p.name, product_sku=p.sku,
            unit=unit.unit_name if unit else p.unit,
            quantity=it.quantity, unit_price=unit_price, cost_price=p.cost_price,
            discount_amount=it.discount_amount, line_total=line_total,
            unit_id=unit.id if unit else None,
            conversion_rate=unit.conversion_rate if unit else None,
        ))
        subtotal += line_total

    invoice.subtotal = subtotal
    invoice.total = max(Decimal("0"), subtotal - sale.discount_amount)
    invoice.cost_total = cost_total
    total_paid = sum((p.amount for p in sale.payments), Decimal("0"))
    invoice.paid_amount = total_paid
    invoice.change_amount = max(Decimal("0"), total_paid - invoice.total)

    for p in sale.payments:
        invoice.payments.append(Payment(method=p.method, amount=p.amount, note=p.note))

    db.add(invoice)
    await db.flush()

    # 4. Trừ tồn — CHO ÂM (offline luôn nhận)
    inv_by_pid = await sales_service._lock_inventory_rows(db, tenant_id, product_ids)
    caused_negative = False
    for pid in sorted(base_qty_needed.keys()):
        inv = inv_by_pid[pid]
        base_qty = base_qty_needed[pid]
        new_balance = inv.quantity - base_qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)
        if new_balance < 0:
            caused_negative = True
        db.add(StockMovement(
            tenant_id=tenant_id, product_id=pid, quantity=-base_qty,
            unit_cost=products[pid].cost_price, type="SALE",
            ref_type="INVOICE", ref_id=invoice.id, balance_after=new_balance,
            created_by=user_id, note="Đơn bán offline" if caused_negative else None,
        ))

    # 5. Sổ quỹ
    for p in sale.payments:
        await cash_service.record_cash_entry(
            db, tenant_id, direction="IN",
            method=cash_service.METHOD_MAP.get(p.method, "CASH"),
            amount=p.amount, category="SALE",
            ref_type="INVOICE", ref_id=invoice.id, created_by=user_id,
            note=f"Thu tiền hóa đơn {invoice.code} (offline)",
        )
    if invoice.change_amount > 0:
        await cash_service.record_cash_entry(
            db, tenant_id, direction="OUT", method="CASH",
            amount=invoice.change_amount, category="CHANGE",
            ref_type="INVOICE", ref_id=invoice.id, created_by=user_id,
            note=f"Tiền thối hóa đơn {invoice.code} (offline)",
        )

    await audit_helper.write_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action=audit_helper.COMPLETE_INVOICE, entity_type="invoice",
        entity_id=invoice.id,
        new_data={"code": invoice.code, "total": invoice.total,
                  "origin": "OFFLINE", "caused_negative": caused_negative},
    )
    return OfflineSyncResultDto(
        client_uuid=sale.client_uuid, status="SYNCED",
        invoice_id=invoice.id, code=invoice.code, caused_negative=caused_negative,
    )


async def sync_offline_sales(
    db: AsyncSession, tenant_id: int, user_id: int, payload: OfflineSyncRequest
) -> OfflineSyncResponse:
    results: list[OfflineSyncResultDto] = []
    for sale in payload.sales:
        try:
            res = await _sync_one(db, tenant_id, user_id, payload.device_id, sale)
            await db.commit()                 # transaction RIÊNG từng đơn
            results.append(res)
        except AppError as e:
            await db.rollback()
            results.append(OfflineSyncResultDto(
                client_uuid=sale.client_uuid, status="FAILED",
                error_code=e.code, error_message=e.message,
            ))
        except Exception as e:                # noqa: BLE001 — gói lỗi không lường
            await db.rollback()
            results.append(OfflineSyncResultDto(
                client_uuid=sale.client_uuid, status="FAILED",
                error_code="SYNC_ERROR", error_message=str(e),
            ))
    return OfflineSyncResponse(results=results)
```
> Kiểm `AppError` có thuộc tính `.code` và `.message` (xem `backend/exceptions.py`). Nếu tên khác (`error_code`, `detail`), chỉnh cho khớp.

- [ ] **Step 5: Thêm route**

Trong `backend/modules/sales/router.py`:
```python
from backend.modules.sales.schemas import OfflineSyncRequest, OfflineSyncResponse
from backend.modules.sales import offline_service

@router.post("/invoices/offline-sync", response_model=OfflineSyncResponse)
async def offline_sync(
    payload: OfflineSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await offline_service.sync_offline_sales(
        db, current_user.tenant_id, current_user.id, payload
    )
```
(Khớp prefix router: nếu router đã có `prefix="/invoices"` thì path là `"/offline-sync"`; nếu router gắn ở `/api/v1` không prefix, dùng `"/invoices/offline-sync"`. Kiểm cách `create`/`complete` khai báo trong file để đặt đúng.)

- [ ] **Step 6: Chạy test → PASS**

Run: `python -m pytest tests/test_offline_sales.py -k offline_sync -v`
Expected: 4 PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/modules/sales/
git commit -m "feat(offline): POST /invoices/offline-sync idempotent + cho âm tồn"
```

---

## TASK BE-4: `GET /reports/offline-negative` (OWNER only)

**Files:**
- Modify: `backend/modules/report/service.py`
- Modify: `backend/modules/report/router.py`
- Test: `tests/test_offline_sales.py`

**Interfaces:**
- Produces `GET /api/v1/reports/offline-negative` → `{ items: [{invoice_id, code, temp_code, sold_at, products: [{product_id, name, balance_after}]}] }`. OWNER only.

- [ ] **Step 1: Viết test**

```python
@pytest.mark.asyncio
async def test_offline_negative_lists_negative_invoices(client, shop):
    h = shop["headers"]
    await client.post("/api/v1/invoices/offline-sync", json={
        "device_id": "dev1",
        "sales": [_sale("uuid-neg-0001", shop["p1"]["id"], qty="250")],
    }, headers=h)
    r = await client.get("/api/v1/reports/offline-negative", headers=h)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert any(it["code"].startswith("HD") for it in items)
    assert any(p["balance_after"].startswith("-") or float(p["balance_after"]) < 0
               for it in items for p in it["products"])
```

- [ ] **Step 2: Chạy test → FAIL** — 404.

Run: `python -m pytest tests/test_offline_sales.py -k offline_negative -v`

- [ ] **Step 3: Service**

Trong `backend/modules/report/service.py`:
```python
from backend.modules.sales.models import Invoice
from backend.modules.inventory.models import StockMovement
from backend.modules.product.models import Product

async def offline_negative_invoices(db, tenant_id: int) -> dict:
    rows = (await db.execute(
        select(StockMovement, Invoice, Product)
        .join(Invoice, Invoice.id == StockMovement.ref_id)
        .join(Product, Product.id == StockMovement.product_id)
        .where(
            StockMovement.tenant_id == tenant_id,
            StockMovement.ref_type == "INVOICE",
            StockMovement.balance_after < 0,
            Invoice.origin == "OFFLINE",
        )
        .order_by(Invoice.completed_at.desc())
    )).all()
    by_inv: dict[int, dict] = {}
    for mv, inv, prod in rows:
        entry = by_inv.setdefault(inv.id, {
            "invoice_id": inv.id, "code": inv.code,
            "temp_code": inv.offline_temp_code,
            "sold_at": inv.completed_at.isoformat() if inv.completed_at else None,
            "products": [],
        })
        entry["products"].append({
            "product_id": prod.id, "name": prod.name,
            "balance_after": f"{mv.balance_after:f}".rstrip("0").rstrip("."),
        })
    return {"items": list(by_inv.values())}
```

- [ ] **Step 4: Route (OWNER only)**

Trong `backend/modules/report/router.py` (theo mẫu `require_role("OWNER")` đã dùng cho `/reports/profit`):
```python
@router.get("/offline-negative")
async def offline_negative(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("OWNER")),
):
    return await service.offline_negative_invoices(db, current_user.tenant_id)
```
(Khớp đúng cách import `require_role` & tên `service` trong file.)

- [ ] **Step 5: Chạy test → PASS**

Run: `python -m pytest tests/test_offline_sales.py -k offline_negative -v`

- [ ] **Step 6: Commit**

```bash
git add backend/modules/report/
git commit -m "feat(offline): GET /reports/offline-negative (OWNER)"
```

- [ ] **Step 7: Chạy toàn bộ test backend offline → PASS**

Run: `python -m pytest tests/test_offline_sales.py -v`
Expected: tất cả PASS.

---

## TASK AND-1: Thêm Room + entities/DAO + Hilt module

**Files:**
- Modify: `android/gradle/libs.versions.toml`, `android/app/build.gradle.kts`
- Create: `core/offline/db/entities/CachedProductEntity.kt`, `CachedUnitEntity.kt`, `OfflineSaleEntity.kt`, `OfflineSaleItemEntity.kt`
- Create: `core/offline/db/dao/CatalogDao.kt`, `OfflineSaleDao.kt`
- Create: `core/offline/db/OfflineDb.kt`, `core/offline/OfflineModule.kt`

**Interfaces:**
- Produces entities & DAOs (xem signatures dưới). `OfflineSaleDao.unsyncedCount(): Flow<Int>`, `insertSale(sale, items)`, `pending(): List<OfflineSaleWithItems>`, `markSynced/markFailed/markSyncing`.
- Produces `OfflineDb` (Room) + Hilt providers cho `CatalogDao`, `OfflineSaleDao`.

- [ ] **Step 1: Thêm version & libs Room**

`libs.versions.toml` — `[versions]` thêm `room = "2.6.1"`; `[libraries]` thêm:
```toml
room-runtime = { module = "androidx.room:room-runtime", version.ref = "room" }
room-ktx = { module = "androidx.room:room-ktx", version.ref = "room" }
room-compiler = { module = "androidx.room:room-compiler", version.ref = "room" }
```

- [ ] **Step 2: Dùng trong `app/build.gradle.kts`**

Trong block `dependencies { ... }`:
```kotlin
    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)
```

- [ ] **Step 3: Tạo entities**

`core/offline/db/entities/CachedProductEntity.kt`:
```kotlin
package com.mykiot.pos.core.offline.db.entities

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "cached_products", indices = [Index("barcode"), Index("name")])
data class CachedProductEntity(
    @PrimaryKey val id: Long,
    val sku: String,
    val barcode: String?,
    val name: String,
    val unit: String,
    val salePrice: String,
    val status: String,
)
```
`CachedUnitEntity.kt`:
```kotlin
package com.mykiot.pos.core.offline.db.entities

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "cached_units", indices = [Index("productId"), Index("barcode")])
data class CachedUnitEntity(
    @PrimaryKey val id: Long,
    val productId: Long,
    val unitName: String,
    val conversionRate: String,
    val salePrice: String?,
    val barcode: String?,
)
```
`OfflineSaleEntity.kt`:
```kotlin
package com.mykiot.pos.core.offline.db.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "offline_sales")
data class OfflineSaleEntity(
    @PrimaryKey val clientUuid: String,
    val tempCode: String,
    val soldAt: String,          // ISO8601 UTC
    val subtotal: String,
    val discount: String,
    val total: String,
    val paidAmount: String,
    val changeAmount: String,
    val paymentsJson: String,    // JSON: [{"method","amount"}]
    val status: String,          // PENDING | SYNCING | SYNCED | FAILED
    val serverInvoiceId: Long? = null,
    val serverCode: String? = null,
    val errorCode: String? = null,
    val errorMessage: String? = null,
    val retryCount: Int = 0,
    val syncedAt: String? = null,
)
```
`OfflineSaleItemEntity.kt`:
```kotlin
package com.mykiot.pos.core.offline.db.entities

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "offline_sale_items", indices = [Index("saleUuid")])
data class OfflineSaleItemEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val saleUuid: String,
    val productId: Long,
    val unitId: Long?,
    val name: String,
    val sku: String,
    val unit: String,
    val unitPrice: String,
    val quantity: String,
    val discount: String,
    val lineTotal: String,
    val conversionRate: String?,
)
```

- [ ] **Step 4: Tạo DAOs**

`core/offline/db/dao/CatalogDao.kt`:
```kotlin
package com.mykiot.pos.core.offline.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.mykiot.pos.core.offline.db.entities.CachedProductEntity
import com.mykiot.pos.core.offline.db.entities.CachedUnitEntity

@Dao
interface CatalogDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertProducts(items: List<CachedProductEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertUnits(items: List<CachedUnitEntity>)

    @Query("DELETE FROM cached_products WHERE id IN (:ids)")
    suspend fun deleteProducts(ids: List<Long>)

    @Query("DELETE FROM cached_units WHERE productId IN (:ids)")
    suspend fun deleteUnitsOfProducts(ids: List<Long>)

    @Query("SELECT COUNT(*) FROM cached_products")
    suspend fun productCount(): Int

    @Query("""
        SELECT * FROM cached_products
        WHERE status = 'ACTIVE' AND (name LIKE '%' || :q || '%' OR sku LIKE '%' || :q || '%')
        LIMIT 30
    """)
    suspend fun search(q: String): List<CachedProductEntity>

    @Query("SELECT * FROM cached_products WHERE barcode = :code LIMIT 1")
    suspend fun byProductBarcode(code: String): CachedProductEntity?

    @Query("SELECT * FROM cached_units WHERE barcode = :code LIMIT 1")
    suspend fun unitByBarcode(code: String): CachedUnitEntity?

    @Query("SELECT * FROM cached_products WHERE id = :id LIMIT 1")
    suspend fun productById(id: Long): CachedProductEntity?
}
```
`core/offline/db/dao/OfflineSaleDao.kt`:
```kotlin
package com.mykiot.pos.core.offline.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import com.mykiot.pos.core.offline.db.entities.OfflineSaleEntity
import com.mykiot.pos.core.offline.db.entities.OfflineSaleItemEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface OfflineSaleDao {
    @Insert suspend fun insertSale(sale: OfflineSaleEntity)
    @Insert suspend fun insertItems(items: List<OfflineSaleItemEntity>)

    @Transaction
    suspend fun insertSaleWithItems(sale: OfflineSaleEntity, items: List<OfflineSaleItemEntity>) {
        insertSale(sale); insertItems(items)
    }

    @Query("SELECT COUNT(*) FROM offline_sales WHERE status IN ('PENDING','FAILED','SYNCING')")
    fun unsyncedCount(): Flow<Int>

    @Query("SELECT * FROM offline_sales WHERE status IN ('PENDING','FAILED') ORDER BY soldAt ASC LIMIT :limit")
    suspend fun loadBatch(limit: Int): List<OfflineSaleEntity>

    @Query("SELECT * FROM offline_sales ORDER BY soldAt DESC")
    fun observeAll(): Flow<List<OfflineSaleEntity>>

    @Query("SELECT * FROM offline_sale_items WHERE saleUuid = :uuid")
    suspend fun itemsOf(uuid: String): List<OfflineSaleItemEntity>

    @Query("UPDATE offline_sales SET status = :status WHERE clientUuid IN (:uuids)")
    suspend fun setStatus(uuids: List<String>, status: String)

    @Query("""UPDATE offline_sales SET status='SYNCED', serverInvoiceId=:invId,
              serverCode=:code, syncedAt=:at, errorCode=NULL, errorMessage=NULL
              WHERE clientUuid=:uuid""")
    suspend fun markSynced(uuid: String, invId: Long, code: String, at: String)

    @Query("""UPDATE offline_sales SET status='FAILED', errorCode=:code,
              errorMessage=:msg, retryCount=retryCount+1 WHERE clientUuid=:uuid""")
    suspend fun markFailed(uuid: String, code: String?, msg: String?)
}
```

- [ ] **Step 5: Tạo `OfflineDb` + Hilt module**

`core/offline/db/OfflineDb.kt`:
```kotlin
package com.mykiot.pos.core.offline.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.mykiot.pos.core.offline.db.dao.CatalogDao
import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import com.mykiot.pos.core.offline.db.entities.CachedProductEntity
import com.mykiot.pos.core.offline.db.entities.CachedUnitEntity
import com.mykiot.pos.core.offline.db.entities.OfflineSaleEntity
import com.mykiot.pos.core.offline.db.entities.OfflineSaleItemEntity

@Database(
    entities = [
        CachedProductEntity::class, CachedUnitEntity::class,
        OfflineSaleEntity::class, OfflineSaleItemEntity::class,
    ],
    version = 1, exportSchema = false,
)
abstract class OfflineDb : RoomDatabase() {
    abstract fun catalogDao(): CatalogDao
    abstract fun offlineSaleDao(): OfflineSaleDao
}
```
`core/offline/OfflineModule.kt`:
```kotlin
package com.mykiot.pos.core.offline

import android.content.Context
import androidx.room.Room
import com.mykiot.pos.core.offline.db.OfflineDb
import com.mykiot.pos.core.offline.db.dao.CatalogDao
import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object OfflineModule {
    @Provides @Singleton
    fun offlineDb(@ApplicationContext ctx: Context): OfflineDb =
        Room.databaseBuilder(ctx, OfflineDb::class.java, "mykiot_offline.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun catalogDao(db: OfflineDb): CatalogDao = db.catalogDao()
    @Provides fun offlineSaleDao(db: OfflineDb): OfflineSaleDao = db.offlineSaleDao()
}
```

- [ ] **Step 6: Build để xác minh Room compile + KSP sinh code**

Run: `cd c:/Users/VuongNV/Downloads/my_kiot/android && ./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL (Room annotation xử lý không lỗi).

- [ ] **Step 7: Commit**

```bash
git add android/gradle/libs.versions.toml android/app/build.gradle.kts android/app/src/main/java/com/mykiot/pos/core/offline/
git commit -m "feat(offline): Room (catalog cache + outbox) + Hilt module"
```

---

## TASK AND-2: CatalogApi + CatalogCache (kéo & làm mới)

**Files:**
- Create: `core/network/dto/CatalogDtos.kt`, `core/network/CatalogApi.kt`
- Modify: `core/network/NetworkModule.kt` (provide CatalogApi)
- Create: `core/offline/CatalogCache.kt`
- Create: `core/offline/DeviceId.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/core/offline/CatalogCacheTest.kt`

**Interfaces:**
- Consumes: `CatalogDao` (AND-1).
- Produces: `CatalogApi.getCatalog(since: String?): CatalogResponseDto`.
- Produces: `CatalogCache.refresh(): ApiResult<Unit>`, `CatalogCache.isEmpty(): Boolean`.
- Produces: `DeviceId.get(): String` (ổn định theo cài đặt app).

- [ ] **Step 1: DTO + API**

`core/network/dto/CatalogDtos.kt`:
```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CatalogUnitDto(
    val id: Long,
    @SerialName("unit_name") val unitName: String,
    @SerialName("conversion_rate") val conversionRate: String,
    @SerialName("sale_price") val salePrice: String? = null,
    val barcode: String? = null,
)

@Serializable
data class CatalogProductDto(
    val id: Long,
    val sku: String,
    val barcode: String? = null,
    val name: String,
    val unit: String,
    @SerialName("sale_price") val salePrice: String,
    val status: String,
    val units: List<CatalogUnitDto> = emptyList(),
)

@Serializable
data class CatalogResponseDto(
    @SerialName("server_time") val serverTime: String,
    val items: List<CatalogProductDto> = emptyList(),
    @SerialName("deleted_ids") val deletedIds: List<Long> = emptyList(),
)
```
`core/network/CatalogApi.kt`:
```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CatalogResponseDto
import retrofit2.http.GET
import retrofit2.http.Query

interface CatalogApi {
    @GET("products/catalog")
    suspend fun getCatalog(@Query("since") since: String? = null): CatalogResponseDto
}
```
Trong `NetworkModule.kt` thêm provider:
```kotlin
    @Provides @Singleton
    fun catalogApi(retrofit: Retrofit): CatalogApi = retrofit.create(CatalogApi::class.java)
```

- [ ] **Step 2: DeviceId**

`core/offline/DeviceId.kt`:
```kotlin
package com.mykiot.pos.core.offline

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceId @Inject constructor(@ApplicationContext ctx: Context) {
    private val prefs = ctx.getSharedPreferences("mykiot_device", Context.MODE_PRIVATE)
    fun get(): String {
        prefs.getString("device_id", null)?.let { return it }
        val id = "and-" + UUID.randomUUID().toString().take(12)
        prefs.edit().putString("device_id", id).apply()
        return id
    }
}
```

- [ ] **Step 3: Viết test CatalogCache (mapping + delete)**

`core/offline/CatalogCacheTest.kt`:
```kotlin
package com.mykiot.pos.core.offline

import com.mykiot.pos.core.network.CatalogApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.dto.CatalogProductDto
import com.mykiot.pos.core.network.dto.CatalogResponseDto
import com.mykiot.pos.core.offline.db.dao.CatalogDao
import com.mykiot.pos.core.offline.db.entities.CachedProductEntity
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class CatalogCacheTest {
    private val api = mockk<CatalogApi>()
    private val dao = mockk<CatalogDao>(relaxed = true)
    private val store = mockk<CatalogSyncStore>(relaxed = true)
    private val cache = CatalogCache(api, dao, store, ErrorMapper())

    @Test
    fun `refresh upserts products and saves server_time`() = runTest {
        coEvery { store.lastSince() } returns null
        coEvery { api.getCatalog(null) } returns CatalogResponseDto(
            serverTime = "2026-06-21T03:00:00Z",
            items = listOf(CatalogProductDto(
                id = 1, sku = "SP1", barcode = "899", name = "Coca",
                unit = "lon", salePrice = "10000", status = "ACTIVE",
            )),
        )
        val slot = slot<List<CachedProductEntity>>()
        coEvery { dao.upsertProducts(capture(slot)) } returns Unit

        cache.refresh()

        assertEquals("Coca", slot.captured.first().name)
        coVerify { store.saveSince("2026-06-21T03:00:00Z") }
    }
}
```

- [ ] **Step 4: Chạy test → FAIL** (chưa có `CatalogCache`, `CatalogSyncStore`).

Run: `./gradlew :app:testDebugUnitTest --tests "*CatalogCacheTest*"`
Expected: compile FAIL.

- [ ] **Step 5: Implement CatalogSyncStore + CatalogCache**

`core/offline/CatalogSyncStore.kt`:
```kotlin
package com.mykiot.pos.core.offline

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
open class CatalogSyncStore @Inject constructor(@ApplicationContext ctx: Context) {
    private val prefs = ctx.getSharedPreferences("mykiot_catalog", Context.MODE_PRIVATE)
    open fun lastSince(): String? = prefs.getString("since", null)
    open fun saveSince(value: String) { prefs.edit().putString("since", value).apply() }
}
```
`core/offline/CatalogCache.kt`:
```kotlin
package com.mykiot.pos.core.offline

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CatalogApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.offline.db.dao.CatalogDao
import com.mykiot.pos.core.offline.db.entities.CachedProductEntity
import com.mykiot.pos.core.offline.db.entities.CachedUnitEntity
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
open class CatalogCache @Inject constructor(
    private val api: CatalogApi,
    private val dao: CatalogDao,
    private val store: CatalogSyncStore,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun isEmpty(): Boolean = dao.productCount() == 0

    open suspend fun refresh(): ApiResult<Unit> = runCatching {
        val resp = api.getCatalog(store.lastSince())
        dao.upsertProducts(resp.items.map {
            CachedProductEntity(it.id, it.sku, it.barcode, it.name, it.unit, it.salePrice, it.status)
        })
        val units = resp.items.flatMap { p ->
            p.units.map { u ->
                CachedUnitEntity(u.id, p.id, u.unitName, u.conversionRate, u.salePrice, u.barcode)
            }
        }
        dao.upsertUnits(units)
        if (resp.deletedIds.isNotEmpty()) {
            dao.deleteUnitsOfProducts(resp.deletedIds)
            dao.deleteProducts(resp.deletedIds)
        }
        store.saveSince(resp.serverTime)
        Unit
    }.fold({ ApiResult.Success(Unit) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

- [ ] **Step 6: Chạy test → PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "*CatalogCacheTest*"`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/ android/app/src/main/java/com/mykiot/pos/core/offline/ android/app/src/test/java/com/mykiot/pos/core/offline/
git commit -m "feat(offline): CatalogApi + CatalogCache (delta refresh) + DeviceId"
```

---

## TASK AND-3: OfflineSaleRepository.enqueue + POS local-first

**Files:**
- Create: `core/offline/OfflineSaleRepository.kt`
- Modify: `feature/pos/data/PosRepository.kt` (search/byBarcode → cache; thêm `enqueueCheckout`)
- Modify: `feature/pos/PosViewModel.kt` (checkout → enqueue + in bill tạm)
- Test: `core/offline/OfflineSaleRepositoryTest.kt`

**Interfaces:**
- Consumes: `OfflineSaleDao`, `CatalogDao`, `DeviceId`, `Cart` (`feature/pos/cart/Cart.kt`), `PaymentInputDto`.
- Produces: `OfflineSaleRepository.enqueue(cart: Cart, payments: List<PaymentInputDto>): EnqueuedSale` với `EnqueuedSale(clientUuid, tempCode, total, paid, change, soldAt, lines)`.
- Produces (PosRepository): `searchLocal(q): List<ProductBriefDto>`, `byBarcodeLocal(code): ProductBriefDto?`.

- [ ] **Step 1: Viết test enqueue (tính tiền + ghi DAO)**

`core/offline/OfflineSaleRepositoryTest.kt`:
```kotlin
package com.mykiot.pos.core.offline

import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import com.mykiot.pos.core.offline.db.entities.OfflineSaleEntity
import com.mykiot.pos.core.offline.db.entities.OfflineSaleItemEntity
import com.mykiot.pos.core.network.dto.PaymentInputDto
import com.mykiot.pos.feature.pos.cart.Cart
import com.mykiot.pos.feature.pos.cart.CartLine
import io.mockk.coEvery
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal

class OfflineSaleRepositoryTest {
    private val dao = mockk<OfflineSaleDao>(relaxed = true)
    private val deviceId = mockk<DeviceId> { coEvery { get() } returns "and-test01" }
    private val seq = mockk<OfflineSeqStore>(relaxed = true).also { coEvery { it.next() } returns 42L }
    private val repo = OfflineSaleRepository(dao, deviceId, seq)

    @Test
    fun `enqueue computes total and persists sale`() = runTest {
        val cart = Cart(lines = listOf(
            CartLine(productId = 1, unitId = null, name = "Coca", sku = "SP1",
                unitName = "lon", unitPrice = BigDecimal("10000"), quantity = BigDecimal("2")),
        ))
        val saleSlot = slot<OfflineSaleEntity>()
        val itemsSlot = slot<List<OfflineSaleItemEntity>>()
        coEvery { dao.insertSaleWithItems(capture(saleSlot), capture(itemsSlot)) } returns Unit

        val res = repo.enqueue(cart, listOf(PaymentInputDto("CASH", "20000")))

        assertEquals("20000.00", saleSlot.captured.total)  // hoặc "20000" tuỳ format chọn
        assertEquals("PENDING", saleSlot.captured.status)
        assertTrue(saleSlot.captured.tempCode.startsWith("TM-and-test01-"))
        assertEquals(1, itemsSlot.captured.size)
        assertEquals(res.clientUuid, saleSlot.captured.clientUuid)
    }
}
```
> Khớp `Cart.total()` / API tính tiền thực tế trong `feature/pos/cart/Cart.kt`. Nếu Cart đã có `subtotal/total`, dùng đúng các hàm đó để khỏi tính lại.

- [ ] **Step 2: Chạy test → FAIL** (chưa có repo/seq).

Run: `./gradlew :app:testDebugUnitTest --tests "*OfflineSaleRepositoryTest*"`

- [ ] **Step 3: OfflineSeqStore + OfflineSaleRepository**

`core/offline/OfflineSeqStore.kt`:
```kotlin
package com.mykiot.pos.core.offline

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
open class OfflineSeqStore @Inject constructor(@ApplicationContext ctx: Context) {
    private val prefs = ctx.getSharedPreferences("mykiot_offline_seq", Context.MODE_PRIVATE)
    @Synchronized open fun next(): Long {
        val v = prefs.getLong("seq", 0L) + 1
        prefs.edit().putLong("seq", v).apply()
        return v
    }
}
```
`core/offline/OfflineSaleRepository.kt`:
```kotlin
package com.mykiot.pos.core.offline

import com.mykiot.pos.core.network.dto.PaymentInputDto
import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import com.mykiot.pos.core.offline.db.entities.OfflineSaleEntity
import com.mykiot.pos.core.offline.db.entities.OfflineSaleItemEntity
import com.mykiot.pos.feature.pos.cart.Cart
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.math.BigDecimal
import java.time.Instant
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

data class EnqueuedLine(val name: String, val qty: BigDecimal, val unitPrice: BigDecimal, val lineTotal: BigDecimal)
data class EnqueuedSale(
    val clientUuid: String, val tempCode: String,
    val total: BigDecimal, val paid: BigDecimal, val change: BigDecimal,
    val soldAt: String, val lines: List<EnqueuedLine>,
)

@Singleton
open class OfflineSaleRepository @Inject constructor(
    private val dao: OfflineSaleDao,
    private val deviceId: DeviceId,
    private val seq: OfflineSeqStore,
) {
    private val json = Json { encodeDefaults = true }

    open suspend fun enqueue(cart: Cart, payments: List<PaymentInputDto>): EnqueuedSale {
        val uuid = UUID.randomUUID().toString()
        val tempCode = "TM-${deviceId.get()}-${"%06d".format(seq.next())}"
        val soldAt = Instant.now().toString()

        val subtotal = cart.lines.fold(BigDecimal.ZERO) { acc, l ->
            acc + (l.unitPrice * l.quantity - l.discount).max(BigDecimal.ZERO)
        }
        val total = (subtotal - cart.invoiceDiscount).max(BigDecimal.ZERO)
        val paid = payments.fold(BigDecimal.ZERO) { acc, p -> acc + BigDecimal(p.amount) }
        val change = (paid - total).max(BigDecimal.ZERO)

        val sale = OfflineSaleEntity(
            clientUuid = uuid, tempCode = tempCode, soldAt = soldAt,
            subtotal = subtotal.toPlainString(), discount = cart.invoiceDiscount.toPlainString(),
            total = total.toPlainString(), paidAmount = paid.toPlainString(),
            changeAmount = change.toPlainString(),
            paymentsJson = json.encodeToString(payments),
            status = "PENDING",
        )
        val items = cart.lines.map { l ->
            OfflineSaleItemEntity(
                saleUuid = uuid, productId = l.productId, unitId = l.unitId,
                name = l.name, sku = l.sku, unit = l.unitName,
                unitPrice = l.unitPrice.toPlainString(), quantity = l.quantity.toPlainString(),
                discount = l.discount.toPlainString(),
                lineTotal = (l.unitPrice * l.quantity - l.discount).max(BigDecimal.ZERO).toPlainString(),
                conversionRate = null,
            )
        }
        dao.insertSaleWithItems(sale, items)
        return EnqueuedSale(uuid, tempCode, total, paid, change, soldAt,
            cart.lines.map { EnqueuedLine(it.name, it.quantity, it.unitPrice,
                (it.unitPrice * it.quantity - it.discount).max(BigDecimal.ZERO)) })
    }
}
```
> `PaymentInputDto` đã `@Serializable` (SalesDtos.kt) nên `encodeToString` chạy được. Khớp các field thực của `CartLine` (discount tên gì) trong `feature/pos/cart/CartLine.kt`.

- [ ] **Step 4: Chạy test → PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "*OfflineSaleRepositoryTest*"`
Expected: PASS (chỉnh assert format tiền cho khớp `toPlainString`).

- [ ] **Step 5: PosRepository đọc cache + PosViewModel enqueue**

Trong `feature/pos/data/PosRepository.kt`: inject thêm `catalogDao: CatalogDao` và `offlineSaleRepository: OfflineSaleRepository`. Đổi `search`/`byBarcode` sang đọc cache (map `CachedProductEntity`/`CachedUnitEntity` → `ProductBriefDto` đang dùng), và thêm:
```kotlin
    open suspend fun searchLocal(q: String): ApiResult<List<ProductBriefDto>> =
        runCatching {
            catalogDao.search(q).map { e ->
                ProductBriefDto(
                    id = e.id, sku = e.sku, name = e.name, unit = e.unit,
                    salePrice = e.salePrice.toDouble(), barcode = e.barcode,
                    matchedUnit = null,
                )
            }
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
```
(Map đúng tất cả field bắt buộc của `ProductBriefDto` — xem `dto/ProductDtos.kt`. Barcode đơn vị: nếu `catalogDao.unitByBarcode(code)` khớp → build `matchedUnit`.)

Trong `feature/pos/PosViewModel.kt`, đổi `checkout(...)` để **luôn enqueue offline** rồi in bill tạm:
```kotlin
    fun checkout(payments: List<PaymentInputDto>, allowDebt: Boolean) {
        val s = _state.value
        if (s.cart.isEmpty()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.pos_cart_empty))) }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            val enq = offlineSaleRepository.enqueue(s.cart, payments)
            _state.update {
                it.copy(
                    loading = false, cart = it.cart.clear(), customer = null, heldDraftId = null,
                    lastInvoiceCode = enq.tempCode, lastOfflineSale = enq,
                )
            }
            syncManager.requestSyncIfOnline()   // AND-4: tự đẩy nếu online
        }
    }
```
(Thêm field `lastOfflineSale: EnqueuedSale?` vào `PosUiState`; bill in dùng `enq` + nhãn "PHIẾU TẠM — CHƯA ĐỒNG BỘ". `syncManager` inject sẽ thêm ở AND-4 — tạm để TODO comment nếu AND-4 chưa xong, hoặc thực hiện AND-4 trước rồi quay lại nối.)

- [ ] **Step 6: Build + chạy unit test POS hiện có không vỡ**

Run: `./gradlew :app:testDebugUnitTest`
Expected: PASS (sửa `PosViewModelTest` nếu nó mock `repository.checkout`; đổi sang mock `offlineSaleRepository.enqueue`).

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/offline/ android/app/src/main/java/com/mykiot/pos/feature/pos/ android/app/src/test/
git commit -m "feat(offline): POS local-first — đọc catalog cache + enqueue đơn offline"
```

---

## TASK AND-4: SyncManager + OfflineSyncApi

**Files:**
- Create: `core/network/dto/OfflineSyncDtos.kt`, `core/network/OfflineSyncApi.kt`
- Modify: `core/network/NetworkModule.kt`
- Create: `core/offline/SyncManager.kt`, `core/offline/NetworkMonitor.kt`
- Test: `core/offline/SyncManagerTest.kt`

**Interfaces:**
- Consumes: `OfflineSaleDao`, `CatalogCache`, `OfflineSyncApi`, `NetworkMonitor`.
- Produces: `SyncManager.unsyncedCount: Flow<Int>`, `syncNow(): SyncOutcome`, `requestSyncIfOnline()`.
- Produces: `OfflineSyncApi.sync(body: OfflineSyncRequestDto): OfflineSyncResponseDto`.

- [ ] **Step 1: DTO + API**

`core/network/dto/OfflineSyncDtos.kt`:
```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OfflineSaleItemReqDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("unit_id") val unitId: Long? = null,
    val quantity: String,
    @SerialName("unit_price") val unitPrice: String? = null,
    @SerialName("discount_amount") val discountAmount: String = "0",
)

@Serializable
data class OfflineSaleReqDto(
    @SerialName("client_uuid") val clientUuid: String,
    @SerialName("temp_code") val tempCode: String,
    @SerialName("sold_at") val soldAt: String,
    @SerialName("discount_amount") val discountAmount: String = "0",
    val items: List<OfflineSaleItemReqDto>,
    val payments: List<PaymentInputDto> = emptyList(),
)

@Serializable
data class OfflineSyncRequestDto(
    @SerialName("device_id") val deviceId: String? = null,
    val sales: List<OfflineSaleReqDto>,
)

@Serializable
data class OfflineSyncResultDto(
    @SerialName("client_uuid") val clientUuid: String,
    val status: String,
    @SerialName("invoice_id") val invoiceId: Long? = null,
    val code: String? = null,
    @SerialName("caused_negative") val causedNegative: Boolean? = null,
    @SerialName("error_code") val errorCode: String? = null,
    @SerialName("error_message") val errorMessage: String? = null,
)

@Serializable
data class OfflineSyncResponseDto(val results: List<OfflineSyncResultDto> = emptyList())
```
`core/network/OfflineSyncApi.kt`:
```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.OfflineSyncRequestDto
import com.mykiot.pos.core.network.dto.OfflineSyncResponseDto
import retrofit2.http.Body
import retrofit2.http.POST

interface OfflineSyncApi {
    @POST("invoices/offline-sync")
    suspend fun sync(@Body body: OfflineSyncRequestDto): OfflineSyncResponseDto
}
```
`NetworkModule.kt` thêm:
```kotlin
    @Provides @Singleton
    fun offlineSyncApi(retrofit: Retrofit): OfflineSyncApi = retrofit.create(OfflineSyncApi::class.java)
```

- [ ] **Step 2: NetworkMonitor**

`core/offline/NetworkMonitor.kt`:
```kotlin
package com.mykiot.pos.core.offline

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
open class NetworkMonitor @Inject constructor(@ApplicationContext private val ctx: Context) {
    open fun isOnline(): Boolean {
        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val net = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(net) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }
}
```

- [ ] **Step 3: Viết test SyncManager (map kết quả → DAO)**

`core/offline/SyncManagerTest.kt`:
```kotlin
package com.mykiot.pos.core.offline

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.OfflineSyncApi
import com.mykiot.pos.core.network.dto.OfflineSyncResponseDto
import com.mykiot.pos.core.network.dto.OfflineSyncResultDto
import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import com.mykiot.pos.core.offline.db.entities.OfflineSaleEntity
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.Test

class SyncManagerTest {
    private val dao = mockk<OfflineSaleDao>(relaxed = true)
    private val api = mockk<OfflineSyncApi>()
    private val catalog = mockk<CatalogCache> { coEvery { refresh() } returns ApiResult.Success(Unit) }
    private val net = mockk<NetworkMonitor> { coEvery { isOnline() } returns true }
    private val deviceId = mockk<DeviceId> { coEvery { get() } returns "and-x" }
    private val sm = SyncManager(dao, api, catalog, net, deviceId)

    private fun sale(uuid: String) = OfflineSaleEntity(
        clientUuid = uuid, tempCode = "TM", soldAt = "2026-06-21T00:00:00Z",
        subtotal = "20000", discount = "0", total = "20000", paidAmount = "20000",
        changeAmount = "0", paymentsJson = """[{"method":"CASH","amount":"20000"}]""",
        status = "PENDING",
    )

    @Test
    fun `syncNow marks synced and failed accordingly`() = runTest {
        coEvery { dao.loadBatch(any()) } returns listOf(sale("u1"), sale("u2")) andThen emptyList()
        coEvery { dao.itemsOf(any()) } returns emptyList()
        coEvery { api.sync(any()) } returns OfflineSyncResponseDto(results = listOf(
            OfflineSyncResultDto("u1", "SYNCED", invoiceId = 10, code = "HD-1"),
            OfflineSyncResultDto("u2", "FAILED", errorCode = "PRODUCT_NOT_FOUND", errorMessage = "x"),
        ))

        sm.syncNow()

        coVerify { dao.markSynced("u1", 10, "HD-1", any()) }
        coVerify { dao.markFailed("u2", "PRODUCT_NOT_FOUND", "x") }
    }
}
```
> `dao.itemsOf` cần trả items thật để build request; ở test này items rỗng vẫn chạy map kết quả. Nếu SyncManager yêu cầu items không rỗng, cung cấp 1 item giả.

- [ ] **Step 4: Chạy test → FAIL** (chưa có SyncManager).

Run: `./gradlew :app:testDebugUnitTest --tests "*SyncManagerTest*"`

- [ ] **Step 5: Implement SyncManager**

`core/offline/SyncManager.kt`:
```kotlin
package com.mykiot.pos.core.offline

import com.mykiot.pos.core.network.OfflineSyncApi
import com.mykiot.pos.core.network.dto.OfflineSaleItemReqDto
import com.mykiot.pos.core.network.dto.OfflineSaleReqDto
import com.mykiot.pos.core.network.dto.OfflineSyncRequestDto
import com.mykiot.pos.core.network.dto.PaymentInputDto
import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import com.mykiot.pos.core.offline.db.entities.OfflineSaleEntity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

data class SyncOutcome(val synced: Int, val failed: Int, val skippedOffline: Boolean = false)

@Singleton
open class SyncManager @Inject constructor(
    private val dao: OfflineSaleDao,
    private val api: OfflineSyncApi,
    private val catalog: CatalogCache,
    private val net: NetworkMonitor,
    private val deviceId: DeviceId,
) {
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    val unsyncedCount: Flow<Int> = dao.unsyncedCount()

    open fun requestSyncIfOnline() {
        if (net.isOnline()) scope.launch { syncNow() }
    }

    open suspend fun syncNow(): SyncOutcome = mutex.withLock {
        if (!net.isOnline()) return@withLock SyncOutcome(0, 0, skippedOffline = true)
        catalog.refresh()  // tiện thể làm mới giá; lỗi không chặn sync
        var synced = 0; var failed = 0
        while (true) {
            val batch = dao.loadBatch(50)
            if (batch.isEmpty()) break
            dao.setStatus(batch.map { it.clientUuid }, "SYNCING")
            val req = OfflineSyncRequestDto(
                deviceId = deviceId.get(),
                sales = batch.map { toReq(it) },
            )
            val resp = runCatching { api.sync(req) }.getOrElse {
                // mất mạng/đứt giữa chừng → revert PENDING, dừng
                dao.setStatus(batch.map { it.clientUuid }, "PENDING")
                return@withLock SyncOutcome(synced, failed)
            }
            for (r in resp.results) {
                if (r.status == "SYNCED") {
                    dao.markSynced(r.clientUuid, r.invoiceId ?: 0, r.code ?: "", Instant.now().toString())
                    synced++
                } else {
                    dao.markFailed(r.clientUuid, r.errorCode, r.errorMessage)
                    failed++
                }
            }
        }
        SyncOutcome(synced, failed)
    }

    private suspend fun toReq(s: OfflineSaleEntity): OfflineSaleReqDto {
        val items = dao.itemsOf(s.clientUuid).map {
            OfflineSaleItemReqDto(
                productId = it.productId, unitId = it.unitId,
                quantity = it.quantity, unitPrice = it.unitPrice, discountAmount = it.discount,
            )
        }
        val payments: List<PaymentInputDto> = json.decodeFromString(s.paymentsJson)
        return OfflineSaleReqDto(
            clientUuid = s.clientUuid, tempCode = s.tempCode, soldAt = s.soldAt,
            discountAmount = s.discount, items = items, payments = payments,
        )
    }
}
```

- [ ] **Step 6: Chạy test → PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "*SyncManagerTest*"`
Expected: PASS.

- [ ] **Step 7: Nối SyncManager vào PosViewModel + app start**

- Inject `SyncManager` vào `PosViewModel` (đã gọi `requestSyncIfOnline()` ở AND-3 Step 5).
- Trong `MyKiotApp` hoặc `MainActivity` (sau login), gọi `syncManager.requestSyncIfOnline()` khi app vào foreground (dùng `ProcessLifecycleOwner` hoặc `LaunchedEffect` ở root composable đã đăng nhập).

- [ ] **Step 8: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ android/app/src/test/
git commit -m "feat(offline): SyncManager + OfflineSyncApi + tự đẩy khi online"
```

---

## TASK AND-5: UI trạng thái sync + màn "Đơn chưa đồng bộ"

**Files:**
- Modify: `feature/pos/PosScreen.kt` (badge + nút "Đồng bộ ngay")
- Create: `feature/offline/UnsyncedSalesViewModel.kt`, `feature/offline/UnsyncedSalesScreen.kt`
- Modify: `navigation/HomeNavHost.kt` + `navigation/HubScreen.kt` (entry vào màn đơn chưa đồng bộ)
- Modify: `android/app/src/main/res/values/strings_misc.xml` (chuỗi tiếng Việt)
- Test: `feature/offline/UnsyncedSalesViewModelTest.kt`

**Interfaces:**
- Consumes: `SyncManager.unsyncedCount`, `SyncManager.syncNow()`, `OfflineSaleDao.observeAll()`.
- Produces: `UnsyncedSalesViewModel.state: StateFlow<UnsyncedUiState>` với `items`, `syncing`, `error`.

- [ ] **Step 1: Strings tiếng Việt**

Thêm vào `strings_misc.xml`:
```xml
<string name="offline_sync_now">Đồng bộ ngay</string>
<string name="offline_unsynced_badge">Chưa đồng bộ: %1$d</string>
<string name="offline_unsynced_title">Đơn chưa đồng bộ</string>
<string name="offline_sync_done">Đã đồng bộ %1$d đơn</string>
<string name="offline_sync_failed_some">%1$d đơn lỗi, cần kiểm tra</string>
<string name="offline_no_network">Không có mạng — đơn sẽ tự đẩy khi có kết nối</string>
<string name="offline_temp_bill_mark">PHIẾU TẠM — CHƯA ĐỒNG BỘ</string>
<string name="offline_empty">Không có đơn nào chờ đồng bộ</string>
```

- [ ] **Step 2: Viết test ViewModel**

`feature/offline/UnsyncedSalesViewModelTest.kt`:
```kotlin
package com.mykiot.pos.feature.offline

import app.cash.turbine.test
import com.mykiot.pos.core.offline.SyncManager
import com.mykiot.pos.core.offline.SyncOutcome
import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class UnsyncedSalesViewModelTest {
    private val dao = mockk<OfflineSaleDao> { coEvery { observeAll() } returns flowOf(emptyList()) }
    private val sync = mockk<SyncManager>(relaxed = true) {
        coEvery { syncNow() } returns SyncOutcome(synced = 3, failed = 0)
    }

    @Test
    fun `syncNow updates message`() = runTest {
        val vm = UnsyncedSalesViewModel(dao, sync)
        vm.syncNow()
        vm.state.test {
            val s = expectMostRecentItem()
            assertEquals(3, s.lastSynced)
        }
    }
}
```

- [ ] **Step 3: Chạy test → FAIL.**

Run: `./gradlew :app:testDebugUnitTest --tests "*UnsyncedSalesViewModelTest*"`

- [ ] **Step 4: Implement ViewModel**

`feature/offline/UnsyncedSalesViewModel.kt`:
```kotlin
package com.mykiot.pos.feature.offline

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.offline.SyncManager
import com.mykiot.pos.core.offline.db.dao.OfflineSaleDao
import com.mykiot.pos.core.offline.db.entities.OfflineSaleEntity
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class UnsyncedUiState(
    val items: List<OfflineSaleEntity> = emptyList(),
    val syncing: Boolean = false,
    val lastSynced: Int? = null,
    val lastFailed: Int? = null,
)

@HiltViewModel
class UnsyncedSalesViewModel @Inject constructor(
    private val dao: OfflineSaleDao,
    private val sync: SyncManager,
) : ViewModel() {
    private val _state = MutableStateFlow(UnsyncedUiState())
    val state: StateFlow<UnsyncedUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            dao.observeAll().collect { list -> _state.update { it.copy(items = list) } }
        }
    }

    fun syncNow() {
        _state.update { it.copy(syncing = true) }
        viewModelScope.launch {
            val r = sync.syncNow()
            _state.update { it.copy(syncing = false, lastSynced = r.synced, lastFailed = r.failed) }
        }
    }
}
```

- [ ] **Step 5: Chạy test → PASS.**

Run: `./gradlew :app:testDebugUnitTest --tests "*UnsyncedSalesViewModelTest*"`

- [ ] **Step 6: Compose screen + badge POS + nav**

- `UnsyncedSalesScreen.kt`: `LazyColumn` liệt kê `state.items` (mã tạm, giờ, tổng tiền, trạng thái; lỗi → ErrorDialog), nút "Đồng bộ ngay" gọi `vm.syncNow()`, empty state dùng `R.string.offline_empty`. Theo pattern các screen list hiện có (vd `InvoiceListScreen.kt`).
- `PosScreen.kt`: thu `syncManager.unsyncedCount` (qua một ViewModel field hoặc collectAsState) → hiện badge `offline_unsynced_badge` + nút `offline_sync_now`.
- `HomeNavHost.kt` + `HubScreen.kt`: thêm route + card "Đơn chưa đồng bộ".

- [ ] **Step 7: Build + commit**

Run: `./gradlew :app:assembleDebug`
```bash
git add android/app/src/main/java/com/mykiot/pos/feature/offline/ android/app/src/main/java/com/mykiot/pos/feature/pos/ android/app/src/main/java/com/mykiot/pos/navigation/ android/app/src/main/res/ android/app/src/test/
git commit -m "feat(offline): UI trạng thái sync + màn đơn chưa đồng bộ"
```

---

## TASK AND-6: In bill tạm + guard cache rỗng + làm mới catalog khi login

**Files:**
- Modify: `feature/pos/PosViewModel.kt` (in bill nhãn tạm; guard cache rỗng khi offline)
- Modify: `feature/pos/PosScreen.kt` (hiển thị nhãn phiếu tạm)
- Modify: login flow (`feature/auth/LoginViewModel.kt` hoặc post-login) gọi `catalogCache.refresh()`
- Test: `feature/pos/PosViewModelTest.kt` (case enqueue, guard)

**Interfaces:**
- Consumes: `CatalogCache.isEmpty()`, `NetworkMonitor.isOnline()`, `OfflineSaleRepository.enqueue`.

- [ ] **Step 1: Test guard "offline + cache rỗng → chặn bán"**

Trong `PosViewModelTest.kt` thêm:
```kotlin
@Test
fun `checkout offline with empty cache shows error`() = runTest {
    coEvery { net.isOnline() } returns false
    coEvery { catalogCache.isEmpty() } returns true
    // cart có 1 dòng (helper sẵn có trong test)
    vm.checkout(listOf(PaymentInputDto("CASH", "10000")), allowDebt = false)
    assertEquals("OFFLINE_NO_CATALOG", vm.state.value.error?.code)
}
```

- [ ] **Step 2: Chạy → FAIL.**

Run: `./gradlew :app:testDebugUnitTest --tests "*PosViewModelTest*"`

- [ ] **Step 3: Thêm guard trong `checkout`**

Đầu `checkout(...)`, sau check cart rỗng:
```kotlin
            if (!net.isOnline() && catalogCache.isEmpty()) {
                _state.update { it.copy(error = ApiError("OFFLINE_NO_CATALOG",
                    res.get(R.string.offline_no_catalog))) }
                return@launch
            }
```
Thêm string `offline_no_catalog` = "Chưa tải dữ liệu để bán offline. Vui lòng kết nối mạng và mở lại app." vào `strings_misc.xml`.

- [ ] **Step 4: Chạy → PASS.**

Run: `./gradlew :app:testDebugUnitTest --tests "*PosViewModelTest*"`

- [ ] **Step 5: In bill nhãn tạm + refresh catalog khi login**

- `printLastInvoice` (hoặc nhánh in cho `lastOfflineSale`): chèn dòng `R.string.offline_temp_bill_mark` + `tempCode`. Khi đơn đã SYNCED và in lại → dùng `serverCode`.
- Sau đăng nhập thành công (LoginViewModel/SessionManager observer): `viewModelScope.launch { catalogCache.refresh() }` để máy luôn có catalog mới nhất khi vào ca.

- [ ] **Step 6: Build + chạy toàn bộ test Android**

Run: `./gradlew :app:testDebugUnitTest && ./gradlew :app:assembleDebug`
Expected: tất cả PASS, build OK.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/ android/app/src/main/res/ android/app/src/test/
git commit -m "feat(offline): in bill tạm + guard cache rỗng + refresh catalog khi login"
```

---

## Self-Review (đã chạy)

**Spec coverage:**
- §3.1 migration invoices → BE-1 ✅ · §3.2 catalog → BE-2 ✅ · §3.3 offline-sync → BE-3 ✅ · §3.4 offline-negative → BE-4 ✅
- §4.1 deps Room → AND-1 ✅ · §4.2 Room schema → AND-1 ✅ · §4.3 CatalogCache → AND-2 ✅ · §4.4 outbox+SyncManager → AND-3/AND-4 ✅ · §4.5 POS refactor → AND-3/AND-6 ✅ · §4.6 UI → AND-5 ✅
- §5 flows → AND-3..AND-6 ✅ · §6 edge cases: idempotent (BE-3, AND-4 revert), product-not-found (BE-3), âm tồn (BE-3/BE-4), unit barcode (AND-2/AND-3 cache units), cache rỗng (AND-6) ✅

**Placeholder scan:** Các điểm "khớp tên file/field thực tế" là chỉ dẫn xác minh khi implement (PosRepository map `ProductBriefDto`, `CartLine` field names), không phải placeholder logic — đã nêu rõ file để đối chiếu. Không có TODO/TBD logic.

**Type consistency:** `client_uuid`(String 36) xuyên suốt BE↔AND; `OfflineSyncResultDto.status` ∈ {SYNCED, FAILED}; DAO `markSynced(uuid, invId, code, at)` khớp SyncManager gọi; `EnqueuedSale`/`SyncOutcome` dùng nhất quán giữa AND-3/4/5.

**Lưu ý xác minh khi code (không chặn plan):**
- `AppError` thuộc tính `.code`/`.message` — kiểm `backend/exceptions.py`, chỉnh BE-3 nếu khác.
- `cash_service.METHOD_MAP` + `record_cash_entry(...)` chữ ký — đã thấy ở `sales/service.py`, dùng y hệt.
- `ProductBriefDto` field bắt buộc (`matchedUnit`, `unit`, `salePrice` kiểu Double) khi map từ cache ở AND-3 — đối chiếu `dto/ProductDtos.kt`.
- Room DAO test bằng mockk (unit), không cần Robolectric; DAO thật được build verify ở AND-1 Step 6.
