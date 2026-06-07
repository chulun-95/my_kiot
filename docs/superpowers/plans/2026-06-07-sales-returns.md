# Trả hàng / Hoàn tiền (Sales Returns) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Trả hàng theo hóa đơn gốc, trả từng phần (chặn trả vượt), cộng lại tồn kho, sinh phiếu chi hoàn tiền (cash book), và **trừ phần trả khỏi mọi báo cáo doanh thu/lợi nhuận**. OWNER mới được hủy phiếu trả.

**Architecture:** Bảng mới `return_orders` + `return_order_items` (chứng từ trả, mã `TH`, ref hóa đơn gốc). Tái dùng: `_lock_inventory_rows` + `StockMovement` (type mới `RETURN`/`CANCEL_RETURN`), `cashbook.record_cash_entry`/`cancel_entries_for_ref` (category mới `REFUND`). Báo cáo trừ phần trả qua helper aggregate trên `return_orders`/`return_order_items`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, pytest (SQLite, create_all), React 18 + TS + Vitest + MSW.

**Quyết định (Gate 1):** trả theo HĐ + partial; hoàn tiền mặt/CK/ví (phiếu chi `REFUND`); KHÔNG trả-nhanh-không-HĐ, KHÔNG phí trả, KHÔNG đổi hàng, KHÔNG trừ công nợ; cộng tồn theo đơn vị cơ bản; giá vốn = snapshot từ invoice_item; report trừ phần trả; hủy phiếu trả = OWNER. `customer.total_spent -= refund` (không đổi `total_orders`).

**Công thức 1 dòng trả:** `rate = conversion_rate or 1`; `refund_per_unit = invoice_item.line_total / invoice_item.quantity` (gồm cả giảm giá dòng gốc); `line_refund = refund_per_unit × qty_trả`; `base_qty = qty_trả × rate`; `cost_line = invoice_item.cost_price × base_qty` (cost_price là giá vốn/đơn vị cơ bản — snapshot).

---

### Task 1: Models + audit + cashbook category + conftest

**Files:**
- Modify: `backend/modules/sales/models.py` (thêm `ReturnOrder`, `ReturnOrderItem`)
- Modify: `backend/shared/audit.py`
- Modify: `backend/modules/cashbook/service.py` (thêm category `REFUND`)
- Modify: `tests/conftest.py`

- [ ] **Step 1: Thêm models vào `backend/modules/sales/models.py`** (cuối file):

```python
class ReturnOrder(Base, AuditMixin):
    __tablename__ = "return_orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_return_orders_tenant_code"),
        Index("idx_return_orders_tenant_completed", "tenant_id", "completed_at"),
        Index("idx_return_orders_invoice", "tenant_id", "invoice_id"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(FKType, ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    invoice_id: Mapped[int] = mapped_column(FKType, ForeignKey("invoices.id"), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(FKType, ForeignKey("customers.id"), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cashier_id: Mapped[int] = mapped_column(FKType, ForeignKey("users.id"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0")
    total_refund: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0")
    cost_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"), server_default="0")
    refund_method: Mapped[str] = mapped_column(String(20), nullable=False, default="CASH", server_default="CASH")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLETED", server_default="COMPLETED")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[int]] = mapped_column(FKType, ForeignKey("users.id"), nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(FKType, ForeignKey("users.id"), nullable=True)

    items: Mapped[list["ReturnOrderItem"]] = relationship(
        "ReturnOrderItem", back_populates="return_order", cascade="all, delete-orphan"
    )


class ReturnOrderItem(Base):
    __tablename__ = "return_order_items"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    return_id: Mapped[int] = mapped_column(FKType, ForeignKey("return_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_item_id: Mapped[Optional[int]] = mapped_column(FKType, ForeignKey("invoice_items.id"), nullable=True)
    product_id: Mapped[int] = mapped_column(FKType, ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    product_sku: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    unit_id: Mapped[Optional[int]] = mapped_column(FKType, ForeignKey("product_units.id", ondelete="SET NULL"), nullable=True)
    conversion_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3), nullable=True)

    return_order: Mapped["ReturnOrder"] = relationship("ReturnOrder", back_populates="items")
```

(Các import `DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func`, `AuditMixin`, `FKType/PKType`, `Optional`, `datetime`, `Decimal` đã có sẵn đầu file — kiểm tra, không thêm trùng.)

- [ ] **Step 2: Audit enums** — thêm vào `backend/shared/audit.py` (sau khối cash book):

```python
# Phase 7 — sales returns
CREATE_SALES_RETURN = "CREATE_SALES_RETURN"
CANCEL_SALES_RETURN = "CANCEL_SALES_RETURN"
```

- [ ] **Step 3: Cash category REFUND** — trong `backend/modules/cashbook/service.py`, thêm `"REFUND"` vào `AUTO_ONLY_CATEGORIES` và `VALID_OUT_CATEGORIES`:

```python
AUTO_ONLY_CATEGORIES = {"SALE", "PURCHASE", "CHANGE", "REFUND"}
VALID_OUT_CATEGORIES = {"PURCHASE", "CHANGE", "SALARY", "OPERATING", "OTHER_OUT", "REFUND"}
```

- [ ] **Step 4: conftest** — đăng ký model trong `tests/conftest.py` (cụm import sales models):

```python
from backend.modules.sales.models import (  # noqa: F401
    Invoice, InvoiceItem, Payment, ReturnOrder, ReturnOrderItem,
)
```

(Thay dòng import sales models hiện có để gồm 2 model mới.)

- [ ] **Step 5: Verify** — Run: `python -c "import tests.conftest"` → exit 0.

- [ ] **Step 6: Commit**

```bash
git add backend/modules/sales/models.py backend/shared/audit.py backend/modules/cashbook/service.py tests/conftest.py
git commit -m "feat(returns): ReturnOrder models + audit + REFUND cash category"
```

---

### Task 2: Migration 006 (prod)

**Files:** Create `alembic/versions/006_sales_returns.py`

- [ ] **Step 1: Tạo migration**

```python
"""add return_orders + return_order_items

Revision ID: 006_sales_returns
Revises: 005_cash_book
Create Date: 2026-06-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_sales_returns"
down_revision: Union[str, None] = "005_cash_book"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "return_orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("cashier_id", sa.BigInteger(), nullable=False),
        sa.Column("subtotal", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("total_refund", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("cost_total", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("refund_method", sa.String(length=20), server_default="CASH", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="COMPLETED", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.BigInteger(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_return_orders_tenant_code"),
    )
    op.create_index("ix_return_orders_tenant_id", "return_orders", ["tenant_id"])
    op.create_index("idx_return_orders_tenant_completed", "return_orders", ["tenant_id", "completed_at"])
    op.create_index("idx_return_orders_invoice", "return_orders", ["tenant_id", "invoice_id"])

    op.create_table(
        "return_order_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.BigInteger(), nullable=False),
        sa.Column("invoice_item_id", sa.BigInteger(), nullable=True),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("product_name", sa.String(length=300), nullable=False),
        sa.Column("product_sku", sa.String(length=50), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("line_total", sa.Numeric(15, 2), nullable=False),
        sa.Column("unit_id", sa.BigInteger(), nullable=True),
        sa.Column("conversion_rate", sa.Numeric(10, 3), nullable=True),
        sa.ForeignKeyConstraint(["return_id"], ["return_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_item_id"], ["invoice_items.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["product_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_return_order_items_return_id", "return_order_items", ["return_id"])


def downgrade() -> None:
    op.drop_index("ix_return_order_items_return_id", "return_order_items")
    op.drop_table("return_order_items")
    op.drop_index("idx_return_orders_invoice", "return_orders")
    op.drop_index("idx_return_orders_tenant_completed", "return_orders")
    op.drop_index("ix_return_orders_tenant_id", "return_orders")
    op.drop_table("return_orders")
```

- [ ] **Step 2: Commit**

```bash
git add alembic/versions/006_sales_returns.py
git commit -m "feat(returns): alembic migration 006 return_orders"
```

---

### Task 3: Schemas

**Files:** Create `backend/modules/sales/return_schemas.py`

- [ ] **Step 1: Tạo schemas**

```python
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RefundMethod = Literal["CASH", "BANK_TRANSFER", "EWALLET"]


class ReturnItemInput(BaseModel):
    invoice_item_id: int
    quantity: Decimal = Field(gt=0)


class ReturnCreateRequest(BaseModel):
    invoice_id: int
    items: list[ReturnItemInput] = Field(min_length=1)
    refund_method: RefundMethod = "CASH"
    reason: Optional[str] = None


class ReturnCancelRequest(BaseModel):
    reason: Optional[str] = None


class ReturnItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    model_config = ConfigDict(from_attributes=True)


class ReturnResponse(BaseModel):
    id: int
    code: str
    invoice_id: int
    customer_id: Optional[int]
    customer_name: Optional[str]
    total_refund: Decimal
    refund_method: str
    status: str
    reason: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime
    items: list[ReturnItemResponse]
    model_config = ConfigDict(from_attributes=True)


class ReturnListItem(BaseModel):
    id: int
    code: str
    invoice_id: int
    customer_name: Optional[str]
    total_refund: Decimal
    refund_method: str
    status: str
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class ReturnListResponse(BaseModel):
    items: list[ReturnListItem]
    pagination: Pagination


# Số đã trả còn lại theo từng dòng hóa đơn (cho FE dựng form)
class ReturnableLine(BaseModel):
    invoice_item_id: int
    product_id: int
    product_name: str
    product_sku: str
    unit: Optional[str]
    sold_quantity: Decimal
    returned_quantity: Decimal
    returnable_quantity: Decimal
    unit_price: Decimal


class ReturnableInvoiceResponse(BaseModel):
    invoice_id: int
    invoice_code: str
    customer_id: Optional[int]
    customer_name: Optional[str]
    lines: list[ReturnableLine]
```

- [ ] **Step 2: Verify** — `python -c "import backend.modules.sales.return_schemas"` → exit 0.
- [ ] **Step 3: Commit**

```bash
git add backend/modules/sales/return_schemas.py
git commit -m "feat(returns): pydantic schemas"
```

---

### Task 4: Service (create/cancel/list/returnable) + tests

**Files:**
- Create: `backend/modules/sales/return_service.py`
- Test: `tests/test_returns.py`

- [ ] **Step 1: Viết test (failing)** — tạo `tests/test_returns.py`:

```python
import pytest


def _auth(t): return {"Authorization": f"Bearer {t}"}


@pytest.fixture
async def shop(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "Coca", "sku": "COC", "sale_price": 12000, "cost_price": 9000,
    }, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 100, "cost_price": 9000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    return {"h": h, "p": p, "token": registered_owner["access_token"]}


async def _sell(client, h, pid, qty, paid=None):
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": pid, "quantity": qty}],
    }, headers=h)).json()
    amt = paid if paid is not None else float(inv["total"])
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": amt}],
    }, headers=h)
    return inv


@pytest.mark.asyncio
async def test_returnable_lists_invoice_lines(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)
    r = await client.get(f"/api/v1/returns/returnable/{inv['id']}", headers=h)
    assert r.status_code == 200
    line = r.json()["lines"][0]
    assert float(line["sold_quantity"]) == 5
    assert float(line["returnable_quantity"]) == 5


@pytest.mark.asyncio
async def test_partial_return_restocks_and_refunds(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)  # total 60000
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]

    r = await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"],
        "items": [{"invoice_item_id": item_id, "quantity": 2}],
        "refund_method": "CASH",
    }, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["code"].startswith("TH")
    assert float(body["total_refund"]) == 24000  # 2 × 12000

    # tồn cộng lại: bán 5 còn 95 → trả 2 → 97
    inv_list = (await client.get("/api/v1/inventory", headers=h)).json()
    qty = next(i["quantity"] for i in inv_list["items"] if i["product_id"] == shop["p"]["id"])
    assert float(qty) == 97

    # cash book có phiếu chi REFUND
    cash = (await client.get("/api/v1/cash-transactions?ref_type=SALES_RETURN", headers=h)).json()
    assert any(i["category"] == "REFUND" and float(i["amount"]) == 24000 for i in cash["items"])


@pytest.mark.asyncio
async def test_cannot_return_more_than_bought(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 3)
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    # trả 2 lần: 2 + 2 = 4 > 3 → lần 2 lỗi
    await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)
    r2 = await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "RETURN_EXCEEDS_SOLD"


@pytest.mark.asyncio
async def test_return_reduces_revenue_report(client, shop):
    from datetime import date
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)  # revenue 60000
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)  # refund 24000
    today = date.today().isoformat()
    rev = (await client.get(f"/api/v1/reports/revenue?from={today}&to={today}", headers=h)).json()
    assert float(rev["total_revenue"]) == 60000 - 24000  # 36000


@pytest.mark.asyncio
async def test_cancel_return_owner_only(client, shop, registered_owner):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 2)
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    ret = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 1}],
    }, headers=h)).json()
    # cashier không hủy được
    await client.post("/api/v1/staff", json={
        "full_name": "C", "phone": "0912333444", "password": "secret123",
    }, headers=h)
    ct = (await client.post("/api/v1/auth/login", json={"phone": "0912333444", "password": "secret123"})).json()["access_token"]
    rc = await client.post(f"/api/v1/returns/{ret['id']}/cancel", json={"reason": "x"}, headers=_auth(ct))
    assert rc.status_code == 403
    # owner hủy được → tồn trừ lại
    ro = await client.post(f"/api/v1/returns/{ret['id']}/cancel", json={"reason": "x"}, headers=h)
    assert ro.status_code == 200
    assert ro.json()["status"] == "CANCELLED"
```

- [ ] **Step 2: Run → FAIL** — Run: `python -m pytest tests/test_returns.py -q` → FAIL (404).

- [ ] **Step 3: Tạo `backend/modules/sales/return_service.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.exceptions import AppError
from backend.modules.cashbook import service as cash_service
from backend.modules.customer.models import Customer
from backend.modules.inventory.models import Inventory, StockMovement
from backend.modules.sales.models import Invoice, InvoiceItem, ReturnOrder, ReturnOrderItem
from backend.modules.sales.return_schemas import ReturnCreateRequest
from backend.modules.sales.service import _lock_inventory_rows, _get_invoice
from backend.shared import audit as audit_helper
from backend.shared.code_generator import generate_code
from backend.shared.pagination import paginate


async def _returned_qty_by_item(db: AsyncSession, tenant_id: int, invoice_id: int) -> dict[int, Decimal]:
    """Tổng đã trả (ACTIVE/COMPLETED) theo invoice_item_id của 1 hóa đơn."""
    rows = (await db.execute(
        select(ReturnOrderItem.invoice_item_id, func.coalesce(func.sum(ReturnOrderItem.quantity), 0))
        .join(ReturnOrder, ReturnOrder.id == ReturnOrderItem.return_id)
        .where(
            ReturnOrder.tenant_id == tenant_id,
            ReturnOrder.invoice_id == invoice_id,
            ReturnOrder.status == "COMPLETED",
        )
        .group_by(ReturnOrderItem.invoice_item_id)
    )).all()
    return {iid: Decimal(str(q or 0)) for iid, q in rows if iid is not None}


async def get_returnable(db: AsyncSession, tenant_id: int, invoice_id: int) -> dict[str, Any]:
    invoice = await _get_invoice(db, tenant_id, invoice_id)
    if invoice.status != "COMPLETED":
        raise AppError(400, "INVOICE_NOT_COMPLETED", "Chỉ trả hàng cho hóa đơn đã hoàn tất")
    returned = await _returned_qty_by_item(db, tenant_id, invoice_id)
    lines = []
    for it in invoice.items:
        already = returned.get(it.id, Decimal("0"))
        lines.append({
            "invoice_item_id": it.id,
            "product_id": it.product_id,
            "product_name": it.product_name,
            "product_sku": it.product_sku,
            "unit": it.unit,
            "sold_quantity": it.quantity,
            "returned_quantity": already,
            "returnable_quantity": it.quantity - already,
            "unit_price": it.unit_price,
        })
    return {
        "invoice_id": invoice.id,
        "invoice_code": invoice.code,
        "customer_id": invoice.customer_id,
        "customer_name": None,
        "lines": lines,
    }


async def create_return(db: AsyncSession, tenant_id: int, user_id: int, payload: ReturnCreateRequest) -> ReturnOrder:
    invoice = await _get_invoice(db, tenant_id, invoice_id=payload.invoice_id)
    if invoice.status != "COMPLETED":
        raise AppError(400, "INVOICE_NOT_COMPLETED", "Chỉ trả hàng cho hóa đơn đã hoàn tất")

    items_by_id = {it.id: it for it in invoice.items}
    returned = await _returned_qty_by_item(db, tenant_id, invoice.id)

    # validate
    for line in payload.items:
        it = items_by_id.get(line.invoice_item_id)
        if it is None:
            raise AppError(400, "INVOICE_ITEM_NOT_FOUND", "Dòng hóa đơn không hợp lệ")
        remaining = it.quantity - returned.get(it.id, Decimal("0"))
        if line.quantity > remaining:
            raise AppError(400, "RETURN_EXCEEDS_SOLD",
                           f"Trả vượt số đã mua (còn có thể trả {remaining})",
                           {"invoice_item_id": it.id, "remaining": str(remaining)})

    code = await generate_code(db, tenant_id, "TH", with_date=True)
    ro = ReturnOrder(
        tenant_id=tenant_id, code=code, invoice_id=invoice.id,
        customer_id=invoice.customer_id, cashier_id=user_id,
        refund_method=payload.refund_method, status="COMPLETED",
        reason=payload.reason, completed_at=datetime.now(tz=timezone.utc), created_by=user_id,
    )
    db.add(ro)
    await db.flush()

    # build items + gom base_qty theo product
    base_qty_by_pid: dict[int, Decimal] = {}
    subtotal = Decimal("0")
    cost_total = Decimal("0")
    for line in payload.items:
        it = items_by_id[line.invoice_item_id]
        rate = it.conversion_rate if it.conversion_rate else Decimal("1")
        refund_per_unit = (it.line_total / it.quantity) if it.quantity else Decimal("0")
        line_refund = (refund_per_unit * line.quantity).quantize(Decimal("0.01"))
        base_qty = (line.quantity * rate).quantize(Decimal("0.001"))
        cost_line = (it.cost_price * base_qty).quantize(Decimal("0.01"))
        subtotal += line_refund
        cost_total += cost_line
        base_qty_by_pid[it.product_id] = base_qty_by_pid.get(it.product_id, Decimal("0")) + base_qty
        db.add(ReturnOrderItem(
            return_id=ro.id, invoice_item_id=it.id, product_id=it.product_id,
            product_name=it.product_name, product_sku=it.product_sku,
            quantity=line.quantity, unit_price=it.unit_price, cost_price=it.cost_price,
            line_total=line_refund, unit_id=it.unit_id, conversion_rate=it.conversion_rate,
        ))

    ro.subtotal = subtotal
    ro.total_refund = subtotal
    ro.cost_total = cost_total

    # cộng tồn (kardex RETURN)
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, list(base_qty_by_pid.keys()))
    for pid in sorted(base_qty_by_pid.keys()):
        inv = inv_by_pid[pid]
        base_qty = base_qty_by_pid[pid]
        new_balance = inv.quantity + base_qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)
        db.add(StockMovement(
            tenant_id=tenant_id, product_id=pid, quantity=base_qty,
            type="RETURN", ref_type="SALES_RETURN", ref_id=ro.id,
            balance_after=new_balance, created_by=user_id,
            note=f"Trả hàng {ro.code}",
        ))

    # hoàn tiền (cash OUT)
    await cash_service.record_cash_entry(
        db, tenant_id, direction="OUT", method=payload.refund_method,
        amount=ro.total_refund, category="REFUND",
        ref_type="SALES_RETURN", ref_id=ro.id, created_by=user_id,
        partner_type=("CUSTOMER" if invoice.customer_id else None),
        partner_id=invoice.customer_id, note=f"Hoàn tiền trả hàng {ro.code}",
    )

    # trừ thống kê KH (không đổi total_orders)
    if invoice.customer_id:
        c = await db.get(Customer, invoice.customer_id)
        if c:
            c.total_spent = max(Decimal("0"), (c.total_spent or Decimal("0")) - ro.total_refund)

    await audit_helper.write_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action=audit_helper.CREATE_SALES_RETURN, entity_type="return_order",
        entity_id=ro.id, new_data={"code": ro.code, "invoice_id": invoice.id, "total_refund": ro.total_refund},
    )
    await db.commit()
    return await get_return(db, tenant_id, ro.id)


async def get_return(db: AsyncSession, tenant_id: int, return_id: int) -> ReturnOrder:
    ro = await db.scalar(
        select(ReturnOrder).where(ReturnOrder.id == return_id, ReturnOrder.tenant_id == tenant_id)
        .options(selectinload(ReturnOrder.items))
    )
    if not ro:
        raise AppError(404, "RETURN_NOT_FOUND", "Phiếu trả không tồn tại")
    return ro


async def cancel_return(db: AsyncSession, tenant_id: int, user_id: int, return_id: int, reason: str | None) -> ReturnOrder:
    ro = await get_return(db, tenant_id, return_id)
    if ro.status == "CANCELLED":
        raise AppError(400, "RETURN_CANCELLED", "Phiếu trả đã bị hủy")

    base_qty_by_pid: dict[int, Decimal] = {}
    for it in ro.items:
        rate = it.conversion_rate if it.conversion_rate else Decimal("1")
        base_qty_by_pid[it.product_id] = base_qty_by_pid.get(it.product_id, Decimal("0")) + (it.quantity * rate)

    inv_by_pid = await _lock_inventory_rows(db, tenant_id, list(base_qty_by_pid.keys()))
    for pid in sorted(base_qty_by_pid.keys()):
        inv = inv_by_pid[pid]
        base_qty = base_qty_by_pid[pid]
        new_balance = inv.quantity - base_qty
        inv.quantity = new_balance
        db.add(StockMovement(
            tenant_id=tenant_id, product_id=pid, quantity=-base_qty,
            type="CANCEL_RETURN", ref_type="SALES_RETURN", ref_id=ro.id,
            balance_after=new_balance, created_by=user_id, note=f"Hủy phiếu trả {ro.code}",
        ))

    await cash_service.cancel_entries_for_ref(
        db, tenant_id, ref_type="SALES_RETURN", ref_id=ro.id, user_id=user_id, reason=reason
    )

    if ro.customer_id:
        c = await db.get(Customer, ro.customer_id)
        if c:
            c.total_spent = (c.total_spent or Decimal("0")) + ro.total_refund

    ro.status = "CANCELLED"
    ro.cancelled_at = datetime.now(tz=timezone.utc)
    ro.cancelled_by = user_id
    ro.cancel_reason = reason

    await audit_helper.write_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action=audit_helper.CANCEL_SALES_RETURN, entity_type="return_order",
        entity_id=ro.id, new_data={"code": ro.code, "reason": reason},
    )
    await db.commit()
    return await get_return(db, tenant_id, ro.id)


async def list_returns(db: AsyncSession, tenant_id: int, *, page: int = 1, limit: int = 20) -> dict[str, Any]:
    stmt = select(ReturnOrder).where(ReturnOrder.tenant_id == tenant_id).order_by(ReturnOrder.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)
```

- [ ] **Step 4: Run tests** (sẽ pass create/restock/refund/exceeds/cancel; `test_return_reduces_revenue_report` còn FAIL tới Task 6). Run: `python -m pytest tests/test_returns.py -q -k "not revenue"` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/sales/return_service.py tests/test_returns.py
git commit -m "feat(returns): service create/cancel/list/returnable + tests"
```

---

### Task 5: Router + mount

**Files:**
- Create: `backend/modules/sales/return_router.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Tạo router**

```python
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user, require_role
from backend.modules.auth.models import User
from backend.modules.sales import return_service
from backend.modules.sales.return_schemas import (
    Pagination,
    ReturnCancelRequest,
    ReturnCreateRequest,
    ReturnListItem,
    ReturnListResponse,
    ReturnResponse,
    ReturnableInvoiceResponse,
)

router = APIRouter(prefix="/api/v1/returns", tags=["returns"])


@router.get("", response_model=ReturnListResponse)
async def list_returns(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    data = await return_service.list_returns(db, user.current_tenant_id, page=page, limit=limit)
    return ReturnListResponse(
        items=[ReturnListItem.model_validate(i) for i in data["items"]],
        pagination=Pagination(**data["pagination"]),
    )


@router.get("/returnable/{invoice_id}", response_model=ReturnableInvoiceResponse)
async def returnable(
    invoice_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    data = await return_service.get_returnable(db, user.current_tenant_id, invoice_id)
    return ReturnableInvoiceResponse(**data)


@router.get("/{return_id}", response_model=ReturnResponse)
async def get_return(
    return_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ro = await return_service.get_return(db, user.current_tenant_id, return_id)
    return ReturnResponse.model_validate(ro)


@router.post("", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    payload: ReturnCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ro = await return_service.create_return(db, user.current_tenant_id, user.id, payload)
    return ReturnResponse.model_validate(ro)


@router.post("/{return_id}/cancel", response_model=ReturnResponse)
async def cancel_return(
    return_id: int,
    payload: ReturnCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    ro = await return_service.cancel_return(db, owner.current_tenant_id, owner.id, return_id, payload.reason)
    return ReturnResponse.model_validate(ro)
```

- [ ] **Step 2: Mount** trong `backend/main.py`: import `from backend.modules.sales.return_router import router as return_router` và `app.include_router(return_router)` (sau sales_router).

- [ ] **Step 3: Run** `python -m pytest tests/test_returns.py -q -k "not revenue"` → PASS.
- [ ] **Step 4: Commit**

```bash
git add backend/modules/sales/return_router.py backend/main.py
git commit -m "feat(returns): router + mount"
```

---

### Task 6: Trừ phần trả khỏi báo cáo

**Files:** Modify `backend/modules/report/service.py`

Thêm helper aggregate returns, rồi trừ ở 5 hàm. Returns dùng `completed_at` + `status='COMPLETED'`.

- [ ] **Step 1: Thêm import + helpers** — đầu `report/service.py` thêm import:

```python
from backend.modules.sales.models import ReturnOrder, ReturnOrderItem
```

Thêm 3 helper (sau phần `_date_range`):

```python
async def _returns_totals(db, tenant_id, start, end):
    row = (await db.execute(
        select(
            func.coalesce(func.sum(ReturnOrder.total_refund), 0),
            func.coalesce(func.sum(ReturnOrder.cost_total), 0),
            func.count(ReturnOrder.id),
        ).where(
            ReturnOrder.tenant_id == tenant_id, ReturnOrder.status == "COMPLETED",
            ReturnOrder.completed_at >= start, ReturnOrder.completed_at < end,
        )
    )).one()
    return Decimal(str(row[0] or 0)), Decimal(str(row[1] or 0)), int(row[2] or 0)


async def _returns_by_product(db, tenant_id, start, end):
    rate = func.coalesce(ReturnOrderItem.conversion_rate, 1)
    rows = (await db.execute(
        select(
            ReturnOrderItem.product_id,
            func.coalesce(func.sum(ReturnOrderItem.quantity * rate), 0),
            func.coalesce(func.sum(ReturnOrderItem.line_total), 0),
            func.coalesce(func.sum(ReturnOrderItem.cost_price * ReturnOrderItem.quantity * rate), 0),
        )
        .join(ReturnOrder, ReturnOrder.id == ReturnOrderItem.return_id)
        .where(
            ReturnOrder.tenant_id == tenant_id, ReturnOrder.status == "COMPLETED",
            ReturnOrder.completed_at >= start, ReturnOrder.completed_at < end,
        )
        .group_by(ReturnOrderItem.product_id)
    )).all()
    return {
        pid: (Decimal(str(q or 0)), Decimal(str(rev or 0)), Decimal(str(cost or 0)))
        for pid, q, rev, cost in rows
    }


async def _returns_by_period(db, tenant_id, start, end, dialect, group_by):
    if dialect == "postgresql":
        period_expr = func.to_char(ReturnOrder.completed_at, "YYYY-MM-DD" if group_by == "day" else "YYYY-MM")
    else:
        period_expr = func.strftime("%Y-%m-%d" if group_by == "day" else "%Y-%m", ReturnOrder.completed_at)
    rows = (await db.execute(
        select(
            period_expr.label("period"),
            func.coalesce(func.sum(ReturnOrder.total_refund), 0),
            func.coalesce(func.sum(ReturnOrder.cost_total), 0),
        ).where(
            ReturnOrder.tenant_id == tenant_id, ReturnOrder.status == "COMPLETED",
            ReturnOrder.completed_at >= start, ReturnOrder.completed_at < end,
        ).group_by("period")
    )).all()
    return {p: (Decimal(str(r or 0)), Decimal(str(c or 0))) for p, r, c in rows}
```

- [ ] **Step 2: Trừ ở `dashboard`** — sau khi tính `today_revenue/today_cost` (dòng ~53-57), thêm:

```python
    ret_refund, ret_cost, _ = await _returns_totals(db, tenant_id, today_start, today_end)
    today_revenue = today_revenue - ret_refund
    today_profit = (today_revenue) - (today_cost - ret_cost)
```

(Đặt TRƯỚC khi `today_profit` được dùng/return; điều chỉnh để `today_profit = (today_revenue) - (today_cost - ret_cost)` — lưu ý today_revenue đã trừ refund.)

- [ ] **Step 3: Trừ ở `revenue`** — sau khi có `total_revenue/total_cost` và `series`:
  - Totals: `r_refund, r_cost, _ = await _returns_totals(db, tenant_id, start, end)`; `total_revenue -= r_refund`; `total_profit = total_revenue - (total_cost - r_cost)`.
  - Series: `rmap = await _returns_by_period(db, tenant_id, start, end, dialect, group_by)`; với mỗi point trừ `rmap.get(period, (0,0))`: `revenue -= rr`, `profit = (revenue) - (cost - rc)`. (Sửa vòng tạo series để áp dụng.)

- [ ] **Step 4: Trừ ở `profit`** — `r_refund, r_cost, _ = await _returns_totals(...)`; `total_revenue -= r_refund`; `total_cost -= r_cost`; `gross_profit = total_revenue - total_cost`.

- [ ] **Step 5: Trừ ở `top_products` & `products_sold`** — sau khi build `items`, lấy `rbp = await _returns_by_product(db, tenant_id, start, end)` và trừ từng item theo product_id: `quantity_sold -= rq`, `revenue -= rrev` (với top_products revenue=net; products_sold trừ cả net_revenue và cost: `net_revenue -= rrev`, `cost -= rcost`), `profit = net_revenue - cost`. SP có item trong kỳ mới hiển thị (SP chỉ bị trả mà không bán trong kỳ là hiếm — chấp nhận bỏ qua ở MVP).

> Implementer: đọc kỹ từng hàm, áp trừ đúng biến. Mục tiêu: con số report = bán − trả. Giữ Decimal.

- [ ] **Step 6: Run** — Run: `python -m pytest tests/test_returns.py tests/test_report.py -q` → all pass (gồm `test_return_reduces_revenue_report`).
- [ ] **Step 7: Commit**

```bash
git add backend/modules/report/service.py
git commit -m "feat(returns): deduct returns from revenue/profit/product reports"
```

---

### Task 7: Frontend — API + MSW + pages + nav

**Files:**
- Create: `frontend/src/api/salesReturn.ts`
- Modify: `frontend/src/__tests__/mocks/handlers.ts`
- Create: `frontend/src/pages/returns/ReturnList.tsx`, `ReturnForm.tsx`, `__tests__/ReturnList.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/AppLayout.tsx`, `frontend/src/pages/invoices/InvoiceDetail.tsx`

- [ ] **Step 1: API client** `frontend/src/api/salesReturn.ts`:

```typescript
import apiClient from './client';

export interface ReturnableLine {
  invoice_item_id: number;
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string | null;
  sold_quantity: number | string;
  returned_quantity: number | string;
  returnable_quantity: number | string;
  unit_price: number | string;
}
export interface ReturnableInvoice {
  invoice_id: number;
  invoice_code: string;
  customer_id: number | null;
  customer_name: string | null;
  lines: ReturnableLine[];
}
export interface ReturnListItem {
  id: number; code: string; invoice_id: number;
  customer_name: string | null; total_refund: number | string;
  refund_method: string; status: string; completed_at: string | null;
}
export interface ReturnListResponse {
  items: ReturnListItem[];
  pagination: { page: number; limit: number; total: number; total_pages: number };
}
export interface ReturnCreatePayload {
  invoice_id: number;
  items: { invoice_item_id: number; quantity: number }[];
  refund_method: 'CASH' | 'BANK_TRANSFER' | 'EWALLET';
  reason?: string;
}

export async function listReturns(params: { page?: number; limit?: number } = {}): Promise<ReturnListResponse> {
  const { data } = await apiClient.get<ReturnListResponse>('/returns', { params });
  return data;
}
export async function getReturnable(invoiceId: number): Promise<ReturnableInvoice> {
  const { data } = await apiClient.get<ReturnableInvoice>(`/returns/returnable/${invoiceId}`);
  return data;
}
export async function createReturn(payload: ReturnCreatePayload) {
  const { data } = await apiClient.post('/returns', payload);
  return data;
}
export async function cancelReturn(id: number, reason?: string) {
  const { data } = await apiClient.post(`/returns/${id}/cancel`, { reason });
  return data;
}
```

- [ ] **Step 2: MSW handlers** — thêm vào handlers.ts:

```typescript
  http.get('*/returns/returnable/:id', ({ params }) =>
    HttpResponse.json({
      invoice_id: Number(params.id), invoice_code: 'HD20260607-001',
      customer_id: null, customer_name: null,
      lines: [{
        invoice_item_id: 10, product_id: 1, product_name: 'Coca 330ml', product_sku: 'COC',
        unit: 'lon', sold_quantity: 5, returned_quantity: 0, returnable_quantity: 5, unit_price: 12000,
      }],
    }),
  ),
  http.get('*/returns', () =>
    HttpResponse.json({
      items: [{
        id: 1, code: 'TH20260607-001', invoice_id: 1, customer_name: null,
        total_refund: 24000, refund_method: 'CASH', status: 'COMPLETED',
        completed_at: '2026-06-07T03:00:00Z',
      }],
      pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
    }),
  ),
  http.post('*/returns', () =>
    HttpResponse.json({ id: 1, code: 'TH20260607-001', invoice_id: 1, customer_id: null,
      customer_name: null, total_refund: 24000, refund_method: 'CASH', status: 'COMPLETED',
      reason: null, completed_at: '2026-06-07T03:00:00Z', created_at: '2026-06-07T03:00:00Z',
      items: [] }, { status: 201 }),
  ),
```

- [ ] **Step 3: ReturnList page + test** — tạo `frontend/src/pages/returns/ReturnList.tsx` (clone pattern list đơn giản: bảng mã/HĐ/khách/hoàn tiền/trạng thái, dùng formatVND/formatDate, EmptyState). Test `ReturnList.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ReturnList from '../ReturnList';

describe('ReturnList', () => {
  it('renders return rows', async () => {
    render(<MemoryRouter><ReturnList /></MemoryRouter>);
    expect(await screen.findByText('Trả hàng')).toBeInTheDocument();
    expect(await screen.findByText('TH20260607-001')).toBeInTheDocument();
    expect(screen.getByText('24.000 VNĐ')).toBeInTheDocument();
  });
});
```

ReturnList.tsx (đầy đủ):

```tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as api from '../../api/salesReturn';
import type { ReturnListResponse } from '../../api/salesReturn';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

export default function ReturnList() {
  const [data, setData] = useState<ReturnListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.listReturns().then(setData).catch((e) => setError(toFriendlyMessage(e))).finally(() => setLoading(false));
  }, []);
  const items = data?.items ?? [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Trả hàng</h1>
      {error && <div role="alert" className="text-sm text-rose-600">{error}</div>}
      <div className="bg-white border border-slate-200 rounded overflow-x-auto">
        {loading ? <div className="p-4"><SkeletonCard /></div> : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600"><tr>
              <th className="px-3 py-2 text-left">Mã phiếu</th>
              <th className="px-3 py-2 text-left">Hóa đơn</th>
              <th className="px-3 py-2 text-left">Thời gian</th>
              <th className="px-3 py-2 text-right">Hoàn tiền</th>
              <th className="px-3 py-2 text-left">Trạng thái</th>
            </tr></thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan={5} className="px-3 py-6"><EmptyState title="Chưa có phiếu trả hàng" /></td></tr>
              ) : items.map((it) => (
                <tr key={it.id} className={`border-t border-slate-100 ${it.status === 'CANCELLED' ? 'opacity-40 line-through' : ''}`}>
                  <td className="px-3 py-2 font-mono text-xs">
                    <Link to={`/returns/${it.id}`} className="text-slate-900 underline">{it.code}</Link>
                  </td>
                  <td className="px-3 py-2">#{it.invoice_id}</td>
                  <td className="px-3 py-2">{formatDate(it.completed_at)}</td>
                  <td className="px-3 py-2 text-right text-rose-700">{formatVND(it.total_refund)}</td>
                  <td className="px-3 py-2">{it.status === 'COMPLETED' ? 'Đã trả' : 'Đã hủy'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: ReturnForm page** — tạo `frontend/src/pages/returns/ReturnForm.tsx`: nhận `?invoice=<id>` query (hoặc nav từ InvoiceDetail), gọi `getReturnable`, render từng dòng với input số lượng trả (max = returnable_quantity, dùng viValidity), chọn refund_method, submit `createReturn` → navigate `/returns`. (Theo pattern AdjustmentForm.) Mọi label tiếng Việt.

- [ ] **Step 5: Wire routes + nav + nút trên InvoiceDetail**
  - App.tsx: lazy import ReturnList/ReturnForm; routes `/returns` (ReturnList), `/returns/new` (ReturnForm) trong AppLayout.
  - AppLayout.tsx: nav item `{ to: '/returns', label: 'Trả hàng', icon: icons.invoice }` (baseNav, vì CASHIER được tạo trả hàng).
  - InvoiceDetail.tsx: thêm nút "Trả hàng" (chỉ khi invoice.status === 'COMPLETED') → `navigate('/returns/new?invoice=' + id)`.

- [ ] **Step 6: Verify + commit**

Run: `cd frontend && npx tsc --noEmit && npx vitest run` → tsc 0, all pass.

```bash
git add frontend/src/api/salesReturn.ts frontend/src/__tests__/mocks/handlers.ts frontend/src/pages/returns frontend/src/App.tsx frontend/src/components/AppLayout.tsx frontend/src/pages/invoices/InvoiceDetail.tsx
git commit -m "feat(returns-fe): return list/form, invoice return button, routes+nav"
```

---

### Task 8: Verify toàn hệ thống

- [ ] **Step 1:** `python -m pytest tests/ -q` → all pass.
- [ ] **Step 2:** `cd frontend && npx tsc --noEmit && npx vitest run` → all pass.

---

## Self-Review

**Spec coverage:** trả theo HĐ + partial + chặn vượt (Task 4 `RETURN_EXCEEDS_SOLD`) ✅; cộng tồn kardex RETURN (Task 4) ✅; hoàn tiền cash REFUND (Task 4) ✅; **trừ report** (Task 6, test `test_return_reduces_revenue_report`) ✅; hủy OWNER-only (Task 5 router) ✅; giá vốn snapshot từ invoice_item ✅; total_spent giảm, total_orders giữ ✅; FE list/form/nút HĐ/nav (Task 7) ✅; migration 006 (Task 2) ✅; audit (Task 1,4) ✅; tiếng Việt ✅.

**Migration checklist:** tenant_id mọi query ✅; audit CREATE/CANCEL ✅; require_role OWNER cho cancel ✅; partial unique không cần (code unique đủ) ✅; conftest đăng ký model (Task 1) ✅.

**Placeholder scan:** Task 6 Step 2-5 và Task 7 Step 4 mô tả vị trí + biến cần sửa thay vì paste full hàm (vì phải chèn vào hàm dài) — kèm code helper đầy đủ; implementer đọc hàm và áp. Đây là hướng dẫn sửa-tại-chỗ có code, không phải placeholder rỗng.

**Type consistency:** service trả ReturnOrder → `ReturnResponse.model_validate` (from_attributes) ✅; cash REFUND trong AUTO_ONLY + VALID_OUT ✅; StockMovement.type RETURN/CANCEL_RETURN (String, không cần migration) ✅.

**Rủi ro:** Task 6 (trừ report) là phần dễ sai nhất — test `test_return_reduces_revenue_report` chốt hàm revenue; nên kiểm thêm dashboard/profit/products_sold thủ công nếu cần. Import vòng: `return_service` import `sales.service` (_lock_inventory_rows,_get_invoice) + `cashbook.service` — một chiều, không vòng. `report.service` import `sales.models` (ReturnOrder) — model, không vòng.
