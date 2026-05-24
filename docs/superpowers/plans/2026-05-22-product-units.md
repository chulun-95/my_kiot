# Product Units (Đơn vị quy đổi) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `product_units` table so warehouses can manage inventory by thùng/lốc instead of individual lon/cái, with automatic conversion to base units for all inventory calculations.

**Architecture:** A new `product_units` table stores conversion units (e.g. thùng=24 lon) per product. Inventory always stored in base unit. `goods_receipt_items` and `invoice_items` gain `unit_id` + `conversion_rate` snapshot columns. Services convert to base qty before touching inventory. Barcode lookup checks `product_units.barcode` as fallback.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async (Mapped/mapped_column), Pydantic v2, Alembic, pytest-asyncio, SQLite (tests) / PostgreSQL (prod), httpx AsyncClient.

**Spec:** `docs/superpowers/specs/2026-05-22-product-units-design.md`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/modules/product/models.py` | Modify | Add `ProductUnit` model; add `units` relationship to `Product` |
| `backend/modules/inventory/models.py` | Modify | Add `unit_id`, `unit_name`, `conversion_rate` to `GoodsReceiptItem` |
| `backend/modules/sales/models.py` | Modify | Add `unit_id`, `conversion_rate` to `InvoiceItem` |
| `alembic/versions/002_product_units.py` | Create | Migration: create table + add columns |
| `tests/conftest.py` | Modify | Import `ProductUnit` so SQLite creates the table |
| `backend/modules/product/schemas.py` | Modify | Add `ProductUnitCreateRequest/UpdateRequest/Response`; update `ProductResponse`, `ProductBriefResponse` |
| `backend/modules/inventory/schemas.py` | Modify | Add `unit_id` to `GoodsReceiptItemInput`; add `units_breakdown` to `InventoryItemResponse` |
| `backend/modules/sales/schemas.py` | Modify | Add `unit_id` to `InvoiceItemInput`; add `conversion_rate` to `InvoiceItemResponse` |
| `backend/shared/audit.py` | Modify | Add 3 audit action constants |
| `backend/modules/product/service.py` | Modify | Add ProductUnit CRUD functions; update `get_product` + `get_by_barcode` |
| `backend/modules/product/router.py` | Modify | Add 4 unit endpoints; update barcode endpoint response |
| `backend/modules/inventory/service.py` | Modify | Fix `old_stock <= 0` bug; add unit_id validation + conversion in create/complete/cancel |
| `backend/modules/sales/service.py` | Modify | Add unit_id validation + conversion in create/update/complete/cancel invoice |
| `backend/modules/inventory/service.py` | Modify | Add `units_breakdown` to `list_inventory` |
| `tests/test_product_units.py` | Create | Integration tests (9 scenarios) |
| `CLAUDE.md` | Modify | Update DDL, pseudocode, API list; remove backlog item |

---

## Task 1: ORM Models + Migration + conftest import

**Files:**
- Modify: `backend/modules/product/models.py`
- Modify: `backend/modules/inventory/models.py`
- Modify: `backend/modules/sales/models.py`
- Create: `alembic/versions/002_product_units.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write failing test (model exists in DB)**

Create `tests/test_product_units.py`:

```python
import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_product_unit_model_exists(client, registered_owner):
    """ProductUnit table must exist — creating a product should return units=[]."""
    h = _auth(registered_owner["access_token"])
    r = await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "units" in body
    assert body["units"] == []
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /Users/vuongnv/Documents/my_kiot
python -m pytest tests/test_product_units.py::test_product_unit_model_exists -v 2>&1 | head -30
```

Expected: FAIL — either `units` missing from response or table doesn't exist.

- [ ] **Step 3: Add `ProductUnit` model to `backend/modules/product/models.py`**

Add at bottom of file (after `ProductImage`). Also add `units` relationship to `Product`:

```python
# In existing Product class, add after the `images` relationship:
    units: Mapped[list["ProductUnit"]] = relationship(
        "ProductUnit",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductUnit.unit_name",
        lazy="selectin",
    )
```

Add new class after `ProductImage`:

```python
class ProductUnit(Base):
    __tablename__ = "product_units"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "product_id", "unit_name",
            name="uq_product_units_tenant_product_unit",
        ),
        Index(
            "uq_product_units_tenant_barcode",
            "tenant_id",
            "barcode",
            unique=True,
            sqlite_where=text("barcode IS NOT NULL"),
            postgresql_where=text("barcode IS NOT NULL"),
        ),
        Index("idx_product_units_product", "tenant_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("tenants.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        FKType, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    unit_name: Mapped[str] = mapped_column(String(30), nullable=False)
    conversion_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False
    )
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    product: Mapped["Product"] = relationship("Product", back_populates="units")
```

Also add these imports that `ProductUnit` needs to the top of `models.py`:

```python
from datetime import datetime
from sqlalchemy import DateTime, UniqueConstraint, func
```

(Check existing imports — `String`, `ForeignKey`, `Index`, `Numeric`, `text` already exist. `Boolean`, `Integer`, `SmallInteger`, `Text` already imported. Add only what's missing.)

- [ ] **Step 4: Add `unit_id`, `unit_name`, `conversion_rate` to `GoodsReceiptItem` in `backend/modules/inventory/models.py`**

In the `GoodsReceiptItem` class, after `line_total` column:

```python
    unit_id: Mapped[int | None] = mapped_column(
        FKType,
        ForeignKey("product_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    unit_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
```

- [ ] **Step 5: Add `unit_id`, `conversion_rate` to `InvoiceItem` in `backend/modules/sales/models.py`**

In the `InvoiceItem` class, after `line_total` column:

```python
    unit_id: Mapped[int | None] = mapped_column(
        FKType,
        ForeignKey("product_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
```

- [ ] **Step 6: Update `tests/conftest.py` to import `ProductUnit`**

Change the product models import line from:
```python
from backend.modules.product.models import Category, Product, ProductImage  # noqa: F401
```
to:
```python
from backend.modules.product.models import Category, Product, ProductImage, ProductUnit  # noqa: F401
```

- [ ] **Step 7: Create Alembic migration `alembic/versions/002_product_units.py`**

```python
"""add product_units table and unit columns to receipt/invoice items

Revision ID: 002_product_units
Revises: 001_initial
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "002_product_units"
down_revision: Union[str, None] = "001_initial"
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

    # Partial unique index for barcode (PostgreSQL and SQLite compatible)
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
```

- [ ] **Step 8: Run test — verify it passes**

```bash
python -m pytest tests/test_product_units.py::test_product_unit_model_exists -v 2>&1 | head -30
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/modules/product/models.py backend/modules/inventory/models.py \
        backend/modules/sales/models.py alembic/versions/002_product_units.py \
        tests/conftest.py tests/test_product_units.py
git commit -m "feat: add ProductUnit ORM model, migration, and item columns"
```

---

## Task 2: Pydantic Schemas

**Files:**
- Modify: `backend/modules/product/schemas.py`
- Modify: `backend/modules/inventory/schemas.py`
- Modify: `backend/modules/sales/schemas.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_product_units.py`:

```python
@pytest.mark.asyncio
async def test_create_product_unit_schema_validation(client, registered_owner):
    """POST /products/{id}/units requires conversion_rate > 1."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()

    # conversion_rate = 1 should be rejected (must be > 1)
    r = await client.post(
        f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "lon", "conversion_rate": 1.0},
        headers=h,
    )
    assert r.status_code == 422, r.text
```

Run: `python -m pytest tests/test_product_units.py::test_create_product_unit_schema_validation -v`
Expected: FAIL (endpoint doesn't exist yet)

- [ ] **Step 2: Add schemas to `backend/modules/product/schemas.py`**

Add after `MessageResponse` (before `CategoryNode.model_rebuild()`):

```python
# ---------- ProductUnit ----------

class ProductUnitCreateRequest(BaseModel):
    unit_name: str = Field(min_length=1, max_length=30)
    conversion_rate: Decimal = Field(gt=1)
    sale_price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=50)

    @field_validator("barcode")
    @classmethod
    def _strip_barcode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class ProductUnitUpdateRequest(BaseModel):
    unit_name: str | None = Field(default=None, min_length=1, max_length=30)
    conversion_rate: Decimal | None = Field(default=None, gt=1)
    sale_price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=50)

    @field_validator("barcode")
    @classmethod
    def _strip_barcode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class ProductUnitResponse(BaseModel):
    id: int
    unit_name: str
    conversion_rate: Decimal
    sale_price: Decimal | None
    barcode: str | None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 3: Update `ProductResponse` to include `units`**

Change:
```python
class ProductResponse(BaseModel):
    id: int
    sku: str
    barcode: str | None
    name: str
    description: str | None
    unit: str
    cost_price: Decimal | None = None
    sale_price: Decimal
    min_stock: int
    image_url: str | None
    status: ProductStatus
    allow_negative: bool
    category_id: int | None
    category_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

To:
```python
class ProductResponse(BaseModel):
    id: int
    sku: str
    barcode: str | None
    name: str
    description: str | None
    unit: str
    cost_price: Decimal | None = None
    sale_price: Decimal
    min_stock: int
    image_url: str | None
    status: ProductStatus
    allow_negative: bool
    category_id: int | None
    category_name: str | None = None
    created_at: datetime
    updated_at: datetime
    units: list[ProductUnitResponse] = []

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Update `ProductBriefResponse` to include `matched_unit` and `units`**

Change `ProductBriefResponse` to:
```python
class ProductBriefResponse(BaseModel):
    """Dùng cho search/barcode lookup ở POS — payload nhẹ.
    cost_price=None khi CASHIER không có quyền xem giá vốn.
    """

    id: int
    sku: str
    barcode: str | None
    name: str
    unit: str
    sale_price: Decimal
    cost_price: Decimal | None = None
    image_url: str | None
    allow_negative: bool
    status: ProductStatus
    units: list[ProductUnitResponse] = []
    matched_unit: ProductUnitResponse | None = None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 5: Add `unit_id` to `GoodsReceiptItemInput` and `unit_name`/`conversion_rate` to `GoodsReceiptItemResponse` in `backend/modules/inventory/schemas.py`**

Change `GoodsReceiptItemInput`:
```python
class GoodsReceiptItemInput(BaseModel):
    product_id: int = Field(ge=1)
    unit_id: int | None = None
    quantity: Decimal = Field(gt=0)
    cost_price: Decimal = Field(ge=0)

    @field_validator("quantity", "cost_price")
    @classmethod
    def _positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("must be non-negative")
        return v
```

Change `GoodsReceiptItemResponse`:
```python
class GoodsReceiptItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    product_sku: str | None = None
    unit_id: int | None = None
    unit_name: str | None = None
    conversion_rate: Decimal | None = None
    quantity: Decimal
    cost_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)
```

Add `UnitBreakdownItem` and update `InventoryItemResponse`:
```python
class UnitBreakdownItem(BaseModel):
    unit_name: str
    conversion_rate: Decimal
    quantity_in_unit: Decimal


class InventoryItemResponse(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    unit: str
    quantity: Decimal
    min_stock: int
    cost_price: Decimal
    sale_price: Decimal
    units_breakdown: list[UnitBreakdownItem] = []
```

- [ ] **Step 6: Add `unit_id` to `InvoiceItemInput` and `conversion_rate` to `InvoiceItemResponse` in `backend/modules/sales/schemas.py`**

Change `InvoiceItemInput`:
```python
class InvoiceItemInput(BaseModel):
    product_id: int = Field(ge=1)
    unit_id: int | None = None
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
```

Change `InvoiceItemResponse`:
```python
class InvoiceItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    unit: str | None
    unit_id: int | None = None
    conversion_rate: Decimal | None = None
    quantity: Decimal
    unit_price: Decimal
    cost_price: Decimal
    discount_amount: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 7: Run full test suite to check no regressions**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -20
```

Expected: All existing tests pass. The new schema test still fails (endpoint not yet created).

- [ ] **Step 8: Commit**

```bash
git add backend/modules/product/schemas.py backend/modules/inventory/schemas.py \
        backend/modules/sales/schemas.py tests/test_product_units.py
git commit -m "feat: add ProductUnit schemas and update item input/response schemas"
```

---

## Task 3: Audit Constants

**Files:**
- Modify: `backend/shared/audit.py`

- [ ] **Step 1: Add 3 audit action constants to `backend/shared/audit.py`**

After the `# Phase 4 — sales` block, add:

```python
# Phase 5 — product units
CREATE_PRODUCT_UNIT = "CREATE_PRODUCT_UNIT"
UPDATE_PRODUCT_UNIT = "UPDATE_PRODUCT_UNIT"
DELETE_PRODUCT_UNIT = "DELETE_PRODUCT_UNIT"
```

- [ ] **Step 2: Commit**

```bash
git add backend/shared/audit.py
git commit -m "feat: add product unit audit action constants"
```

---

## Task 4: ProductUnit Service CRUD + Updated barcode lookup

**Files:**
- Modify: `backend/modules/product/service.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_product_units.py`:

```python
@pytest.mark.asyncio
async def test_create_product_unit(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()

    r = await client.post(
        f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "sale_price": 240000, "barcode": "8934563012345"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    u = r.json()
    assert u["unit_name"] == "thùng"
    assert float(u["conversion_rate"]) == 24.0
    assert float(u["sale_price"]) == 240000.0
    assert u["barcode"] == "8934563012345"


@pytest.mark.asyncio
async def test_list_product_units_in_product_response(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )

    r = await client.get(f"/api/v1/products/{p['id']}", headers=h)
    assert r.status_code == 200
    units = r.json()["units"]
    assert len(units) == 1
    assert units[0]["unit_name"] == "thùng"


@pytest.mark.asyncio
async def test_barcode_lookup_via_product_unit(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "barcode": "1111111111111"},
        headers=h,
    )

    r = await client.get("/api/v1/products/barcode/1111111111111", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == p["id"]
    assert body["matched_unit"] is not None
    assert body["matched_unit"]["unit_name"] == "thùng"


@pytest.mark.asyncio
async def test_delete_product_unit_blocked_by_draft(client, registered_owner):
    """Cannot delete unit if a DRAFT receipt uses it."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    # Create DRAFT receipt using this unit
    await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
    }, headers=h)

    r = await client.delete(f"/api/v1/products/{p['id']}/units/{u['id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "UNIT_IN_USE"
```

Run: `python -m pytest tests/test_product_units.py -k "unit" -v 2>&1 | tail -30`
Expected: FAIL (endpoints not exist)

- [ ] **Step 2: Add ProductUnit service functions to `backend/modules/product/service.py`**

Add imports at top of service.py (after existing imports):
```python
from backend.modules.product.models import Category, Product, ProductImage, ProductUnit
```
(Update existing import line — `ProductUnit` is new)

Add these functions after `get_by_barcode`:

```python
# ====================================================================
# PRODUCT UNITS
# ====================================================================

async def _get_unit(
    db: AsyncSession, tenant_id: int, product_id: int, unit_id: int
) -> ProductUnit:
    unit = await db.scalar(
        select(ProductUnit).where(
            ProductUnit.id == unit_id,
            ProductUnit.tenant_id == tenant_id,
            ProductUnit.product_id == product_id,
        )
    )
    if not unit:
        raise AppError(404, "UNIT_NOT_FOUND", "Đơn vị không tồn tại")
    return unit


async def list_product_units(
    db: AsyncSession, tenant_id: int, product_id: int
) -> list[ProductUnit]:
    await get_product(db, tenant_id, product_id)
    rows = (
        await db.execute(
            select(ProductUnit)
            .where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.product_id == product_id,
            )
            .order_by(ProductUnit.unit_name)
        )
    ).scalars().all()
    return list(rows)


async def create_product_unit(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    product_id: int,
    payload: "ProductUnitCreateRequest",
) -> ProductUnit:
    await get_product(db, tenant_id, product_id)

    if payload.barcode:
        existing = await db.scalar(
            select(ProductUnit.id).where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.barcode == payload.barcode,
            )
        )
        if existing:
            raise AppError(409, "BARCODE_EXISTS", f"Barcode '{payload.barcode}' đã tồn tại")

    unit = ProductUnit(
        tenant_id=tenant_id,
        product_id=product_id,
        unit_name=payload.unit_name,
        conversion_rate=payload.conversion_rate,
        sale_price=payload.sale_price,
        barcode=payload.barcode,
    )
    db.add(unit)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "UNIT_EXISTS", f"Đơn vị '{payload.unit_name}' đã tồn tại cho sản phẩm này")

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.CREATE_PRODUCT_UNIT,
        entity_type="product_unit",
        entity_id=unit.id,
        new_data={
            "product_id": product_id,
            "unit_name": unit.unit_name,
            "conversion_rate": unit.conversion_rate,
            "sale_price": unit.sale_price,
            "barcode": unit.barcode,
        },
    )
    await db.commit()
    await db.refresh(unit)
    return unit


async def update_product_unit(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    product_id: int,
    unit_id: int,
    payload: "ProductUnitUpdateRequest",
) -> ProductUnit:
    unit = await _get_unit(db, tenant_id, product_id, unit_id)

    old_snapshot = {
        "unit_name": unit.unit_name,
        "conversion_rate": unit.conversion_rate,
        "sale_price": unit.sale_price,
        "barcode": unit.barcode,
    }

    new_barcode = payload.barcode if payload.barcode is not None else None
    if new_barcode and new_barcode != unit.barcode:
        existing = await db.scalar(
            select(ProductUnit.id).where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.barcode == new_barcode,
                ProductUnit.id != unit_id,
            )
        )
        if existing:
            raise AppError(409, "BARCODE_EXISTS", f"Barcode '{new_barcode}' đã tồn tại")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(unit, k, v)

    new_values = {k: getattr(unit, k) for k in old_snapshot}
    old_diff, new_diff = audit_helper.diff_changes(old_snapshot, new_values)

    try:
        if new_diff:
            await audit_helper.write_audit(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                action=audit_helper.UPDATE_PRODUCT_UNIT,
                entity_type="product_unit",
                entity_id=unit.id,
                old_data=old_diff,
                new_data=new_diff,
            )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "UNIT_EXISTS", "Tên đơn vị hoặc barcode đã tồn tại")

    await db.refresh(unit)
    return unit


async def delete_product_unit(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    product_id: int,
    unit_id: int,
) -> None:
    from backend.modules.inventory.models import GoodsReceipt, GoodsReceiptItem
    from backend.modules.sales.models import Invoice, InvoiceItem

    unit = await _get_unit(db, tenant_id, product_id, unit_id)

    draft_receipt = await db.scalar(
        select(GoodsReceiptItem.id)
        .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptItem.receipt_id)
        .where(
            GoodsReceiptItem.unit_id == unit_id,
            GoodsReceipt.status == "DRAFT",
        )
        .limit(1)
    )
    if draft_receipt:
        raise AppError(409, "UNIT_IN_USE", "Đơn vị đang được dùng trong phiếu nhập nháp")

    draft_invoice = await db.scalar(
        select(InvoiceItem.id)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            InvoiceItem.unit_id == unit_id,
            Invoice.status == "DRAFT",
        )
        .limit(1)
    )
    if draft_invoice:
        raise AppError(409, "UNIT_IN_USE", "Đơn vị đang được dùng trong hóa đơn nháp")

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.DELETE_PRODUCT_UNIT,
        entity_type="product_unit",
        entity_id=unit.id,
        old_data={
            "product_id": product_id,
            "unit_name": unit.unit_name,
            "conversion_rate": unit.conversion_rate,
        },
    )
    await db.delete(unit)
    await db.commit()
```

- [ ] **Step 3: Update `get_product` to load units via `selectinload`**

Current `get_product` loads only `selectinload(Product.category)`. Since we set `lazy="selectin"` on the `units` relationship, they'll auto-load. But update the explicit `options()` for clarity — the existing `get_product` becomes:

```python
async def get_product(
    db: AsyncSession, tenant_id: int, product_id: int
) -> Product:
    product = await db.scalar(
        select(Product)
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
        .options(selectinload(Product.category), selectinload(Product.units))
    )
    if not product:
        raise AppError(404, "PRODUCT_NOT_FOUND", "Sản phẩm không tồn tại")
    return product
```

- [ ] **Step 4: Update `get_by_barcode` to return `tuple[Product, ProductUnit | None]`**

Replace the existing `get_by_barcode` function:

```python
async def get_by_barcode(
    db: AsyncSession, tenant_id: int, barcode: str
) -> tuple["Product", "ProductUnit | None"]:
    # 1. Check products.barcode first
    product = await db.scalar(
        select(Product)
        .where(
            Product.tenant_id == tenant_id,
            Product.barcode == barcode,
            Product.deleted_at.is_(None),
        )
        .options(selectinload(Product.category), selectinload(Product.units))
    )
    if product:
        return product, None

    # 2. Check product_units.barcode
    unit = await db.scalar(
        select(ProductUnit).where(
            ProductUnit.tenant_id == tenant_id,
            ProductUnit.barcode == barcode,
        )
    )
    if unit:
        product = await get_product(db, tenant_id, unit.product_id)
        return product, unit

    raise AppError(404, "PRODUCT_NOT_FOUND", "Không có sản phẩm với barcode này")
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_product_units.py -k "unit" -v 2>&1 | tail -30
```

Expected: FAIL (router endpoints still missing)

- [ ] **Step 6: Commit**

```bash
git add backend/modules/product/service.py
git commit -m "feat: add ProductUnit service CRUD and updated barcode lookup"
```

---

## Task 5: Product Router — Unit Endpoints

**Files:**
- Modify: `backend/modules/product/router.py`

- [ ] **Step 1: Add 4 unit endpoints and update barcode endpoint in `backend/modules/product/router.py`**

First, update the import at the top of router.py to include new schemas:

```python
from backend.modules.product.schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryResponse,
    CategoryTreeResponse,
    MessageResponse,
    ProductBriefResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductSearchResponse,
    ProductUnitCreateRequest,
    ProductUnitResponse,
    ProductUnitUpdateRequest,
)
```

Update the service import to include new functions:
```python
from backend.modules.product import service as svc
```
(No change needed — svc.create_product_unit, etc. all live on the imported module)

Update the `get_by_barcode` endpoint. Find this endpoint:
```python
@product_router.get("/barcode/{barcode}", response_model=ProductBriefResponse)
async def get_by_barcode(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = await svc.get_by_barcode(db, current_user.tenant_id, barcode)
    ...
```

Replace with:
```python
@product_router.get("/barcode/{barcode}", response_model=ProductBriefResponse)
async def get_by_barcode(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product, matched_unit = await svc.get_by_barcode(db, current_user.tenant_id, barcode)
    show_cost = current_user.role == "OWNER"
    data = ProductBriefResponse.model_validate(product)
    if not show_cost:
        data.cost_price = None
    data.matched_unit = (
        ProductUnitResponse.model_validate(matched_unit) if matched_unit else None
    )
    return data
```

Add 4 new unit endpoints (add after the barcode endpoint, before categories section):

```python
# ====================================================================
# PRODUCT UNITS
# ====================================================================

@product_router.get(
    "/{product_id}/units",
    response_model=list[ProductUnitResponse],
)
async def list_units(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.list_product_units(db, current_user.tenant_id, product_id)


@product_router.post(
    "/{product_id}/units",
    response_model=ProductUnitResponse,
    status_code=201,
    dependencies=[Depends(require_role("OWNER"))],
)
async def create_unit(
    product_id: int,
    payload: ProductUnitCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.create_product_unit(
        db, current_user.tenant_id, current_user.id, product_id, payload
    )


@product_router.put(
    "/{product_id}/units/{unit_id}",
    response_model=ProductUnitResponse,
    dependencies=[Depends(require_role("OWNER"))],
)
async def update_unit(
    product_id: int,
    unit_id: int,
    payload: ProductUnitUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.update_product_unit(
        db, current_user.tenant_id, current_user.id, product_id, unit_id, payload
    )


@product_router.delete(
    "/{product_id}/units/{unit_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("OWNER"))],
)
async def delete_unit(
    product_id: int,
    unit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await svc.delete_product_unit(
        db, current_user.tenant_id, current_user.id, product_id, unit_id
    )
    return {"message": "Xóa đơn vị thành công"}
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_product_units.py -v 2>&1 | tail -30
```

Expected: All 5 product unit tests PASS. (Excluding the goods receipt / sales tests that come later.)

- [ ] **Step 3: Run full suite to check no regressions**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -20
```

Expected: All existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/modules/product/router.py
git commit -m "feat: add product unit CRUD endpoints and updated barcode lookup"
```

---

## Task 6: Inventory Service — Conversion Logic + Bug Fix

**Files:**
- Modify: `backend/modules/inventory/service.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_product_units.py`:

```python
@pytest.mark.asyncio
async def test_goods_receipt_with_unit_converts_to_base(client, registered_owner):
    """2 thùng × 24 = 48 lon. Inventory must show 48."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000, "cost_price": 0},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
    }, headers=h)).json()

    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert float(item["quantity"]) == 48.0


@pytest.mark.asyncio
async def test_goods_receipt_cost_per_base_unit(client, registered_owner):
    """cost_per_base = 240,000 / 24 = 10,000/lon."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Pepsi", "unit": "lon", "sale_price": 10000, "cost_price": 0},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    r = await client.get(f"/api/v1/products/{p['id']}", headers=h)
    assert float(r.json()["cost_price"]) == 10000.0
```

Run: `python -m pytest tests/test_product_units.py -k "receipt" -v 2>&1 | tail -20`
Expected: FAIL

- [ ] **Step 2: Add `_get_product_unit` helper in `backend/modules/inventory/service.py`**

Add after `_validate_products`:

```python
async def _get_product_unit_if_given(
    db: AsyncSession, tenant_id: int, product_id: int, unit_id: int | None
) -> "ProductUnit | None":
    if unit_id is None:
        return None
    from backend.modules.product.models import ProductUnit
    unit = await db.scalar(
        select(ProductUnit).where(
            ProductUnit.id == unit_id,
            ProductUnit.tenant_id == tenant_id,
            ProductUnit.product_id == product_id,
        )
    )
    if not unit:
        raise AppError(404, "UNIT_NOT_FOUND", f"Đơn vị id={unit_id} không tồn tại hoặc không thuộc sản phẩm này")
    return unit
```

- [ ] **Step 3: Update `create_goods_receipt` to snapshot `unit_name` + `conversion_rate`**

In `create_goods_receipt`, replace the items creation loop:

```python
    code = await generate_code(db, tenant_id, "NK", with_date=True)
    total = Decimal("0")
    items_to_add: list[GoodsReceiptItem] = []
    for item in payload.items:
        unit = await _get_product_unit_if_given(db, tenant_id, item.product_id, item.unit_id)
        line_total = (item.quantity * item.cost_price).quantize(Decimal("0.01"))
        items_to_add.append(
            GoodsReceiptItem(
                product_id=item.product_id,
                unit_id=unit.id if unit else None,
                unit_name=unit.unit_name if unit else None,
                conversion_rate=unit.conversion_rate if unit else None,
                quantity=item.quantity,
                cost_price=item.cost_price,
                line_total=line_total,
            )
        )
        total += line_total
```

- [ ] **Step 4: Update `update_goods_receipt` items section**

In `update_goods_receipt`, replace the items loop when `payload.items is not None`:

```python
        total = Decimal("0")
        for it in payload.items:
            unit = await _get_product_unit_if_given(db, tenant_id, it.product_id, it.unit_id)
            line_total = (it.quantity * it.cost_price).quantize(Decimal("0.01"))
            receipt.items.append(
                GoodsReceiptItem(
                    product_id=it.product_id,
                    unit_id=unit.id if unit else None,
                    unit_name=unit.unit_name if unit else None,
                    conversion_rate=unit.conversion_rate if unit else None,
                    quantity=it.quantity,
                    cost_price=it.cost_price,
                    line_total=line_total,
                )
            )
            total += line_total
```

- [ ] **Step 5: Update `complete_goods_receipt` — fix `old_stock <= 0` bug + add conversion**

Replace the core computation loop in `complete_goods_receipt` (from the `qty_by_pid` aggregation to the `StockMovement` add):

```python
    receipt.status = "COMPLETED"
    receipt.completed_at = datetime.now(tz=timezone.utc)

    for pid in sorted(set(it.product_id for it in receipt.items)):
        inv = inv_by_pid[pid]
        product = products[pid]

        old_stock = inv.quantity
        old_cost = product.cost_price

        # Aggregate base_qty and cost_value across all lines for this product
        sum_cost_value = Decimal("0")
        sum_base_qty = Decimal("0")
        for it in receipt.items:
            if it.product_id == pid:
                rate = Decimal(it.conversion_rate or 1)
                base_qty_line = it.quantity * rate
                cost_per_base = (it.cost_price / rate).quantize(Decimal("0.000001"))
                sum_cost_value += cost_per_base * base_qty_line
                sum_base_qty += base_qty_line

        in_cost = (sum_cost_value / sum_base_qty).quantize(Decimal("0.01")) if sum_base_qty > 0 else old_cost

        # BUG FIX: use old_stock <= 0, not denom <= 0
        if old_stock <= 0:
            new_cost = in_cost
        else:
            denom = old_stock + sum_base_qty
            new_cost = (
                (old_stock * old_cost + sum_base_qty * in_cost) / denom
            ).quantize(Decimal("0.01"))

        if new_cost != old_cost:
            await audit_helper.write_price_history(
                db,
                tenant_id=tenant_id,
                product_id=product.id,
                field="cost_price",
                old_value=old_cost,
                new_value=new_cost,
                ref_type=audit_helper.PRICE_REF_GOODS_RECEIPT,
                ref_id=receipt.id,
                changed_by=user_id,
            )
            product.cost_price = new_cost

        new_balance = old_stock + sum_base_qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)

        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=pid,
                quantity=sum_base_qty,
                unit_cost=in_cost,
                type="RECEIPT",
                ref_type="GOODS_RECEIPT",
                ref_id=receipt.id,
                balance_after=new_balance,
                created_by=user_id,
            )
        )
```

- [ ] **Step 6: Update `cancel_goods_receipt` — use conversion_rate snapshot for COMPLETED reversal**

In `cancel_goods_receipt`, in the COMPLETED → bút toán ngược section, replace:
```python
    qty_by_pid: dict[int, Decimal] = {}
    for it in receipt.items:
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + it.quantity
```
with:
```python
    qty_by_pid: dict[int, Decimal] = {}
    for it in receipt.items:
        rate = Decimal(it.conversion_rate or 1)
        base_qty = it.quantity * rate
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + base_qty
```

- [ ] **Step 7: Run inventory tests**

```bash
python -m pytest tests/test_product_units.py -k "receipt" -v 2>&1 | tail -20
python -m pytest tests/test_inventory.py -v -q 2>&1 | tail -20
```

Expected: Both receipt conversion tests PASS. Existing inventory tests still pass.

- [ ] **Step 8: Commit**

```bash
git add backend/modules/inventory/service.py
git commit -m "feat: add unit conversion to goods receipt create/complete/cancel; fix old_stock<=0 bug"
```

---

## Task 7: Sales Service — Conversion Logic

**Files:**
- Modify: `backend/modules/sales/service.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_product_units.py`:

```python
@pytest.mark.asyncio
async def test_invoice_with_unit_deducts_base_qty(client, registered_owner):
    """Sell 1 thùng (×24). Inventory should decrease by 24 lon."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Coca", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "sale_price": 240000},
        headers=h,
    )).json()

    # Stock up 48 lon
    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 48, "cost_price": 8000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    # Sell 1 thùng
    inv_data = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 1, "unit_price": 240000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv_data['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 240000}],
    }, headers=h)

    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert float(item["quantity"]) == 24.0  # 48 - 24 = 24
```

Run: `python -m pytest tests/test_product_units.py::test_invoice_with_unit_deducts_base_qty -v 2>&1 | tail -20`
Expected: FAIL

- [ ] **Step 2: Add `_get_product_unit_if_given` helper in `backend/modules/sales/service.py`**

Add after `_validate_products`:

```python
async def _get_product_unit_if_given(
    db: AsyncSession, tenant_id: int, product_id: int, unit_id: int | None
) -> "ProductUnit | None":
    if unit_id is None:
        return None
    from backend.modules.product.models import ProductUnit
    unit = await db.scalar(
        select(ProductUnit).where(
            ProductUnit.id == unit_id,
            ProductUnit.tenant_id == tenant_id,
            ProductUnit.product_id == product_id,
        )
    )
    if not unit:
        raise AppError(404, "UNIT_NOT_FOUND", f"Đơn vị id={unit_id} không tồn tại hoặc không thuộc sản phẩm này")
    return unit
```

- [ ] **Step 3: Update `create_invoice` items loop to snapshot conversion_rate and set correct unit**

In `create_invoice`, replace the items loop:

```python
        for it in payload.items:
            p = products[it.product_id]
            unit = await _get_product_unit_if_given(db, tenant_id, it.product_id, it.unit_id)
            unit_price, line_total = _compute_line(it, p, unit)
            invoice.items.append(
                InvoiceItem(
                    product_id=p.id,
                    product_name=p.name,
                    product_sku=p.sku,
                    unit=unit.unit_name if unit else p.unit,
                    unit_id=unit.id if unit else None,
                    conversion_rate=unit.conversion_rate if unit else None,
                    quantity=it.quantity,
                    unit_price=unit_price,
                    cost_price=p.cost_price,
                    discount_amount=it.discount_amount,
                    line_total=line_total,
                )
            )
            subtotal += line_total
```

Also update `_compute_line` to accept optional unit:

```python
def _compute_line(
    item, product: Product, unit=None
) -> tuple[Decimal, Decimal]:
    if item.unit_price is not None:
        unit_price = item.unit_price
    elif unit is not None and unit.sale_price is not None:
        unit_price = unit.sale_price
    elif unit is not None:
        unit_price = (product.sale_price * unit.conversion_rate).quantize(Decimal("0.01"))
    else:
        unit_price = product.sale_price
    line_subtotal = unit_price * item.quantity
    line_total = (line_subtotal - item.discount_amount).quantize(Decimal("0.01"))
    if line_total < 0:
        line_total = Decimal("0")
    return unit_price, line_total
```

- [ ] **Step 4: Update `update_invoice` items loop similarly**

In `update_invoice`, replace the items loop:

```python
        subtotal = Decimal("0")
        for it in payload.items:
            p = products[it.product_id]
            unit = await _get_product_unit_if_given(db, tenant_id, it.product_id, it.unit_id)
            unit_price, line_total = _compute_line(it, p, unit)
            invoice.items.append(
                InvoiceItem(
                    product_id=p.id,
                    product_name=p.name,
                    product_sku=p.sku,
                    unit=unit.unit_name if unit else p.unit,
                    unit_id=unit.id if unit else None,
                    conversion_rate=unit.conversion_rate if unit else None,
                    quantity=it.quantity,
                    unit_price=unit_price,
                    cost_price=p.cost_price,
                    discount_amount=it.discount_amount,
                    line_total=line_total,
                )
            )
            subtotal += line_total
```

- [ ] **Step 5: Update `complete_invoice` to use `conversion_rate` for base_qty**

Replace the cost/inventory section in `complete_invoice`:

```python
    # 3. Kiểm tra tồn — gom toàn bộ thiếu (dùng base_qty)
    qty_needed_base: dict[int, Decimal] = {}
    for item in invoice.items:
        rate = Decimal(item.conversion_rate or 1)
        base_qty = item.quantity * rate
        qty_needed_base[item.product_id] = qty_needed_base.get(item.product_id, Decimal("0")) + base_qty

    shortages = []
    for pid, need in qty_needed_base.items():
        product = products[pid]
        have = inv_by_pid[pid].quantity
        if have < need and not product.allow_negative:
            shortages.append({
                "product_id": pid,
                "product_name": product.name,
                "need": str(need),
                "have": str(have),
            })
    if shortages:
        raise AppError(
            400,
            "INSUFFICIENT_STOCK",
            "Không đủ tồn kho",
            {"shortages": shortages},
        )

    # 4. Snapshot giá vốn TẠI THỜI ĐIỂM COMPLETE (per base unit)
    cost_total = Decimal("0")
    for item in invoice.items:
        p = products[item.product_id]
        item.cost_price = p.cost_price   # cost per base unit
        rate = Decimal(item.conversion_rate or 1)
        base_qty = item.quantity * rate
        cost_total += (item.cost_price * base_qty).quantize(Decimal("0.01"))
    invoice.cost_total = cost_total

    # 5. Trạng thái + tiền
    invoice.status = "COMPLETED"
    invoice.completed_at = datetime.now(tz=timezone.utc)
    invoice.paid_amount = total_paid
    invoice.change_amount = max(Decimal("0"), total_paid - invoice.total)

    # 6. Lưu payments
    for p in payload.payments:
        invoice.payments.append(
            Payment(method=p.method, amount=p.amount, note=p.note)
        )

    # 7. Trừ tồn + ghi kardex (dùng base_qty)
    for pid in sorted(qty_needed_base.keys()):
        inv = inv_by_pid[pid]
        qty = qty_needed_base[pid]
        new_balance = inv.quantity - qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)

        unit_cost = products[pid].cost_price

        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=pid,
                quantity=-qty,
                unit_cost=unit_cost,
                type="SALE",
                ref_type="INVOICE",
                ref_id=invoice.id,
                balance_after=new_balance,
                created_by=user_id,
            )
        )
```

- [ ] **Step 6: Update `cancel_invoice` to use conversion_rate snapshot for reversal**

In `cancel_invoice`, in the COMPLETED → bút toán ngược section, replace:
```python
    qty_by_pid: dict[int, Decimal] = {}
    for it in invoice.items:
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + it.quantity
```
with:
```python
    qty_by_pid: dict[int, Decimal] = {}
    for it in invoice.items:
        rate = Decimal(it.conversion_rate or 1)
        base_qty = it.quantity * rate
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + base_qty
```

- [ ] **Step 7: Run tests**

```bash
python -m pytest tests/test_product_units.py::test_invoice_with_unit_deducts_base_qty -v
python -m pytest tests/test_sales.py -q 2>&1 | tail -10
```

Expected: Invoice unit test PASS. All sales tests still pass.

- [ ] **Step 8: Commit**

```bash
git add backend/modules/sales/service.py
git commit -m "feat: add unit conversion to invoice create/update/complete/cancel"
```

---

## Task 8: Inventory Display — `units_breakdown`

**Files:**
- Modify: `backend/modules/inventory/service.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_product_units.py`:

```python
@pytest.mark.asyncio
async def test_inventory_units_breakdown(client, registered_owner):
    """Inventory response should show units_breakdown."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 48, "cost_price": 8000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert "units_breakdown" in item
    breakdown = item["units_breakdown"]
    assert len(breakdown) == 1
    assert breakdown[0]["unit_name"] == "thùng"
    assert float(breakdown[0]["conversion_rate"]) == 24.0
    assert float(breakdown[0]["quantity_in_unit"]) == 2.0  # 48 / 24
```

Run: `python -m pytest tests/test_product_units.py::test_inventory_units_breakdown -v`
Expected: FAIL (`units_breakdown` not in response)

- [ ] **Step 2: Update `list_inventory` in `backend/modules/inventory/service.py`**

Add import at top: `from backend.modules.product.models import ProductUnit`

Replace the `items` construction in `list_inventory`:

```python
    base = base.order_by(Product.name).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(base)).all()

    # Load product_units for breakdown
    product_ids = [product.id for _, product in rows]
    units_by_pid: dict[int, list] = {}
    if product_ids:
        unit_rows = (
            await db.execute(
                select(ProductUnit)
                .where(
                    ProductUnit.tenant_id == tenant_id,
                    ProductUnit.product_id.in_(product_ids),
                )
                .order_by(ProductUnit.unit_name)
            )
        ).scalars().all()
        for u in unit_rows:
            units_by_pid.setdefault(u.product_id, []).append(u)

    items = [
        {
            "product_id": product.id,
            "product_sku": product.sku,
            "product_name": product.name,
            "unit": product.unit,
            "quantity": inv.quantity,
            "min_stock": product.min_stock,
            "cost_price": product.cost_price,
            "sale_price": product.sale_price,
            "units_breakdown": [
                {
                    "unit_name": u.unit_name,
                    "conversion_rate": u.conversion_rate,
                    "quantity_in_unit": (inv.quantity / u.conversion_rate).quantize(Decimal("0.001")),
                }
                for u in units_by_pid.get(product.id, [])
            ],
        }
        for inv, product in rows
    ]
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_product_units.py::test_inventory_units_breakdown -v
python -m pytest tests/test_inventory.py -q 2>&1 | tail -10
```

Expected: Both pass.

- [ ] **Step 4: Commit**

```bash
git add backend/modules/inventory/service.py
git commit -m "feat: add units_breakdown to inventory list response"
```

---

## Task 9: Integration Tests (remaining scenarios)

**Files:**
- Modify: `tests/test_product_units.py`

- [ ] **Step 1: Add remaining integration tests to `tests/test_product_units.py`**

```python
@pytest.mark.asyncio
async def test_product_unit_duplicate_unit_name(client, registered_owner):
    """Cannot create two units with the same name for the same product."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )
    r = await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 12},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_product_unit_duplicate_barcode_cross_product(client, registered_owner):
    """Barcode must be unique within tenant across all products."""
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={"name": "P1", "sale_price": 1000}, headers=h)).json()
    p2 = (await client.post("/api/v1/products", json={"name": "P2", "sale_price": 1000}, headers=h)).json()
    await client.post(f"/api/v1/products/{p1['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "barcode": "SHARED-BC"},
        headers=h,
    )
    r = await client.post(f"/api/v1/products/{p2['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "barcode": "SHARED-BC"},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_update_product_unit(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={"name": "Bia", "unit": "lon", "sale_price": 10000}, headers=h)).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    r = await client.put(f"/api/v1/products/{p['id']}/units/{u['id']}",
        json={"sale_price": 250000},
        headers=h,
    )
    assert r.status_code == 200
    assert float(r.json()["sale_price"]) == 250000.0
    assert r.json()["unit_name"] == "thùng"  # unchanged


@pytest.mark.asyncio
async def test_delete_product_unit_success(client, registered_owner):
    """Can delete unit when no DRAFT transactions use it."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={"name": "Bia", "unit": "lon", "sale_price": 10000}, headers=h)).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    r = await client.delete(f"/api/v1/products/{p['id']}/units/{u['id']}", headers=h)
    assert r.status_code == 200

    r2 = await client.get(f"/api/v1/products/{p['id']}/units", headers=h)
    assert r2.json() == []


@pytest.mark.asyncio
async def test_cashier_cannot_create_unit(client, registered_owner):
    """CASHIER role must get 403 on POST /products/{id}/units."""
    h_owner = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={"name": "Bia", "unit": "lon", "sale_price": 10000}, headers=h_owner)).json()

    # Create a cashier
    cashier_resp = await client.post("/api/v1/staff", json={
        "full_name": "Cashier Test",
        "phone": "0987654321",
        "password": "secret123",
        "role": "CASHIER",
    }, headers=h_owner)
    assert cashier_resp.status_code == 201, cashier_resp.text

    login = await client.post("/api/v1/auth/login", json={
        "phone": "0987654321",
        "password": "secret123",
    })
    h_cashier = _auth(login.json()["access_token"])

    r = await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h_cashier,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cancel_completed_receipt_with_unit_restores_base_qty(client, registered_owner):
    """Cancel completed receipt → stock restored by base_qty."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    # Verify stock = 48
    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert float(item["quantity"]) == 48.0

    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/cancel",
        json={"reason": "Test"}, headers=h)

    inv2 = (await client.get("/api/v1/inventory", headers=h)).json()
    item2 = next(i for i in inv2["items"] if i["product_id"] == p["id"])
    assert float(item2["quantity"]) == 0.0
```

- [ ] **Step 2: Run all product unit tests**

```bash
python -m pytest tests/test_product_units.py -v 2>&1 | tail -40
```

Expected: All 15+ tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -q 2>&1 | tail -20
```

Expected: All tests pass with no regressions.

- [ ] **Step 4: Commit**

```bash
git add tests/test_product_units.py
git commit -m "test: add comprehensive integration tests for product units feature"
```

---

## Task 10: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add `product_units` DDL after `product_images` in Phần 2**

Under "Phần 2: Master Data — Sản phẩm, Khách hàng, NCC", after the `product_images` DDL block, add:

```sql
CREATE TABLE product_units (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    unit_name       VARCHAR(30) NOT NULL,           -- 'thùng', 'lốc', 'hộp'
    conversion_rate DECIMAL(10,3) NOT NULL,          -- 1 đơn vị này = N đơn vị cơ bản (> 1)
    sale_price      DECIMAL(15,2),                  -- giá bán riêng (null = product.sale_price × rate)
    barcode         VARCHAR(50),                    -- barcode riêng của đơn vị này
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, product_id, unit_name)
);

CREATE UNIQUE INDEX uq_product_units_tenant_barcode
  ON product_units (tenant_id, barcode) WHERE barcode IS NOT NULL;

CREATE INDEX idx_product_units_product
  ON product_units (tenant_id, product_id);
```

- [ ] **Step 2: Update `goods_receipt_items` DDL in Phần 4**

Add to the end of the `goods_receipt_items` DDL:
```sql
    unit_id         BIGINT REFERENCES product_units(id) ON DELETE SET NULL,
    unit_name       VARCHAR(30),          -- snapshot
    conversion_rate DECIMAL(10,3)         -- snapshot (null or 1 = base unit)
```

- [ ] **Step 3: Update `invoice_items` DDL in Phần 3**

Add to the end of the `invoice_items` DDL:
```sql
    unit_id         BIGINT REFERENCES product_units(id) ON DELETE SET NULL,
    conversion_rate DECIMAL(10,3)         -- snapshot (null or 1 = base unit)
```

- [ ] **Step 4: Update `complete_goods_receipt` pseudocode in Business Logic section**

Update the pseudocode to show conversion logic:
```python
for item in receipt.items:
    rate = Decimal(item.conversion_rate or 1)
    base_qty = item.quantity * rate           # 2 thùng × 24 = 48 lon
    cost_per_base = item.cost_price / rate    # 240,000 ÷ 24 = 10,000/lon

    old_stock = inv.quantity
    if old_stock <= 0:                        # BUG FIX: was denom <= 0
        new_cost = cost_per_base
    else:
        new_cost = (old_stock * old_cost + base_qty * cost_per_base) / (old_stock + base_qty)

    inv.quantity += base_qty                  # +48 lon
    # StockMovement: quantity=+base_qty, unit_cost=cost_per_base
```

- [ ] **Step 5: Update `complete_invoice` pseudocode**

Update cost_total and stock deduction to use base_qty:
```python
for item in invoice.items:
    rate = Decimal(item.conversion_rate or 1)
    base_qty = item.quantity * rate           # 1 thùng × 24 = 24 lon
    item.cost_price = product.cost_price      # snapshot cost per base unit
    cost_total += item.cost_price * base_qty  # 10,000 × 24 = 240,000
    inv.quantity -= base_qty                  # -24 lon
    # StockMovement: quantity=-base_qty, unit_cost=item.cost_price
```

- [ ] **Step 6: Add product unit endpoints to API list**

Under "Products & Categories" API section, add:
```
GET    /api/v1/products/{id}/units           DS đơn vị quy đổi
POST   /api/v1/products/{id}/units           Tạo đơn vị mới          [OWNER only]
PUT    /api/v1/products/{id}/units/{uid}     Sửa đơn vị              [OWNER only]
DELETE /api/v1/products/{id}/units/{uid}     Xóa đơn vị              [OWNER only]
```

- [ ] **Step 7: Remove backlog item #9 from backlog table (thùng/lốc conversion)**

In the backlog table, remove the row for item #9 (unit conversion / thùng → lon).

Also update `conftest.py` import note in Phần 2: note that `product_units` migration is `002_product_units`.

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with product_units DDL, API endpoints, pseudocode"
```

---

## Acceptance Checklist

- [ ] `python -m pytest tests/test_product_units.py -v` — all pass
- [ ] `python -m pytest tests/ -q` — no regressions
- [ ] `GET /api/v1/products/{id}` returns `units: [...]`
- [ ] `POST /api/v1/products/{id}/units` with `conversion_rate=1` returns 422
- [ ] `GET /api/v1/products/barcode/{barcode}` returns `matched_unit` when barcode belongs to unit
- [ ] `POST /api/v1/goods-receipts` with `unit_id` snapshots `unit_name` + `conversion_rate`
- [ ] `complete_goods_receipt` with 2 thùng×24 → inventory shows 48 lon, cost_price = 10,000
- [ ] `complete_invoice` with 1 thùng×24 → inventory decreases 24 lon
- [ ] `cancel_goods_receipt` with unit → restores base qty
- [ ] `GET /api/v1/inventory` returns `units_breakdown`
- [ ] CASHIER cannot POST/PUT/DELETE product units (403)
