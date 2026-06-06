# Báo cáo "Sản phẩm đã bán theo khoảng ngày" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm báo cáo liệt kê TẤT CẢ sản phẩm đã bán trong một khoảng ngày (số lượng quy về đơn vị cơ bản, doanh thu, giảm giá, doanh thu thuần, giá vốn, lợi nhuận gộp, tỷ suất %), có sort động + phân trang + lọc theo nhóm hàng; đồng thời sửa bug đơn vị quy đổi trong `/top-products`.

**Architecture:** Endpoint read-only `GET /api/v1/reports/products-sold` (OWNER-only) mở rộng từ `report_service.top_products`. Aggregate trên `invoice_items` join `invoices` (chỉ `COMPLETED`, lọc `tenant_id` + khoảng `completed_at`). Tự count distinct product qua subquery (KHÔNG dùng `paginate()` chung vì nó `.scalars()` chỉ lấy 1 cột). FE thêm trang `ProductsSoldPage` clone từ `TopProductsPage`, thêm phân trang + header sort + dropdown nhóm hàng.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async, Pydantic v2, pytest (SQLite test / PostgreSQL prod), React 18 + TypeScript + Vitest + MSW.

**Công thức (đã verify trong `backend/modules/sales/service.py:144-156, 375-382`):**
- `unit_price` = giá mỗi **đơn vị bán**; `cost_price` = giá vốn mỗi **đơn vị cơ bản**; `rate = COALESCE(conversion_rate, 1)`.
- `quantity_sold` (đơn vị cơ bản) = `Σ(quantity × rate)`
- `revenue` (doanh thu gộp, trước giảm) = `Σ(unit_price × quantity)`
- `discount` = `Σ(discount_amount)`
- `net_revenue` (doanh thu thuần) = `Σ(line_total)`
- `cost` (giá vốn) = `Σ(cost_price × quantity × rate)`
- `profit` (lợi nhuận gộp) = `net_revenue − cost`
- `margin_pct` = `profit / net_revenue × 100` (0 nếu `net_revenue = 0`)

**Quyết định scope đã chốt (Gate 1):** cột đầy đủ kiểu KiotViet; OWNER-only; có lọc nhóm hàng; quy số lượng & giá vốn về đơn vị cơ bản + fix `top_products`. Chỉ tính hóa đơn `COMPLETED`. Giảm giá toàn hóa đơn (`Invoice.discount_amount`) KHÔNG phân bổ về SP (chỉ dùng `invoice_items.discount_amount`). Lọc nhóm hàng = so khớp `Product.category_id` hiện tại (không gồm SP của nhóm con). Không cần migration; read-only nên không ghi audit log.

---

### Task 1: Backend — Pydantic schemas cho báo cáo

**Files:**
- Modify: `backend/modules/report/schemas.py` (thêm vào cuối file, trước/sau khối Stock summary)

- [ ] **Step 1: Thêm schemas**

Thêm vào cuối `backend/modules/report/schemas.py`:

```python
# ---------- Products Sold (báo cáo SP đã bán) ----------

ProductsSoldSortBy = Literal["revenue", "quantity", "profit"]
SortOrder = Literal["asc", "desc"]


class ProductsSoldItem(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    quantity_sold: Decimal      # đơn vị cơ bản
    revenue: Decimal            # doanh thu gộp (trước giảm giá)
    discount: Decimal
    net_revenue: Decimal        # doanh thu thuần
    cost: Decimal               # giá vốn
    profit: Decimal             # lợi nhuận gộp
    margin_pct: Decimal         # tỷ suất % (= profit / net_revenue * 100)


class ProductsSoldTotals(BaseModel):
    quantity_sold: Decimal
    revenue: Decimal
    discount: Decimal
    net_revenue: Decimal
    cost: Decimal
    profit: Decimal


class ProductsSoldPagination(BaseModel):
    page: int
    limit: int
    total: int           # tổng số SP (distinct) khớp bộ lọc
    total_pages: int


class ProductsSoldResponse(BaseModel):
    from_date: date
    to_date: date
    sort_by: ProductsSoldSortBy
    order: SortOrder
    category_id: int | None
    items: list[ProductsSoldItem]
    totals: ProductsSoldTotals
    pagination: ProductsSoldPagination
```

`Literal`, `Decimal`, `date`, `BaseModel` đã được import sẵn ở đầu file — không thêm import.

- [ ] **Step 2: Verify tsc/import không lỗi**

Run: `python -c "import backend.modules.report.schemas"`
Expected: không lỗi (exit 0).

- [ ] **Step 3: Commit**

```bash
git add backend/modules/report/schemas.py
git commit -m "feat(report): add products-sold response schemas"
```

---

### Task 2: Backend — Viết test integration (failing) cho endpoint mới

**Files:**
- Modify: `tests/test_report.py` (thêm khối test mới sau khối "Top products")

Test đi qua HTTP client (theo đúng pattern các test hiện có). Fixture `shop` đã có sẵn (Owner + p1 Coca giá 12000/vốn 9000 tồn 100, p2 Pepsi giá 25000/vốn 20000 tồn 50). Helper `_complete_invoice(client, headers, product_id, quantity)` đã có.

- [ ] **Step 1: Thêm các test**

Thêm vào `tests/test_report.py` (sau dòng kết thúc `test_top_products_excludes_cancelled`, trước khối "Profit"):

```python
# ===================================================================
# Products sold (báo cáo SP đã bán)
# ===================================================================

@pytest.mark.asyncio
async def test_products_sold_basic(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 5)   # net 60000, cost 45000
    await _complete_invoice(client, h, shop["p2"]["id"], 3)   # net 75000, cost 60000

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}", headers=h
    )
    assert r.status_code == 200
    body = r.json()
    # default sort = revenue desc → p2 (75000) đứng đầu
    items = body["items"]
    assert len(items) == 2
    assert items[0]["product_id"] == shop["p2"]["id"]
    assert float(items[0]["quantity_sold"]) == 3
    assert float(items[0]["revenue"]) == 75000
    assert float(items[0]["net_revenue"]) == 75000
    assert float(items[0]["cost"]) == 60000
    assert float(items[0]["profit"]) == 15000
    # totals
    assert float(body["totals"]["net_revenue"]) == 135000
    assert float(body["totals"]["cost"]) == 105000
    assert float(body["totals"]["profit"]) == 30000
    # pagination
    assert body["pagination"]["total"] == 2
    assert body["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_products_sold_sort_by_quantity(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 5)   # qty 5
    await _complete_invoice(client, h, shop["p2"]["id"], 3)   # qty 3

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}"
        f"&sort_by=quantity&order=desc",
        headers=h,
    )
    items = r.json()["items"]
    assert items[0]["product_id"] == shop["p1"]["id"]  # qty 5 > 3


@pytest.mark.asyncio
async def test_products_sold_pagination(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 5)
    await _complete_invoice(client, h, shop["p2"]["id"], 3)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}&page=1&limit=1",
        headers=h,
    )
    body = r.json()
    assert len(body["items"]) == 1
    assert body["pagination"]["total"] == 2
    assert body["pagination"]["total_pages"] == 2
    # totals luôn tính trên TOÀN BỘ, không bị phân trang
    assert float(body["totals"]["net_revenue"]) == 135000


@pytest.mark.asyncio
async def test_products_sold_category_filter(client, shop):
    h = shop["headers"]
    # Tạo nhóm hàng + gán p1 vào nhóm
    cat = (await client.post("/api/v1/categories", json={"name": "Nước ngọt"}, headers=h)).json()
    await client.put(
        f"/api/v1/products/{shop['p1']['id']}",
        json={"category_id": cat["id"]},
        headers=h,
    )
    await _complete_invoice(client, h, shop["p1"]["id"], 2)
    await _complete_invoice(client, h, shop["p2"]["id"], 1)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}&category_id={cat['id']}",
        headers=h,
    )
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == shop["p1"]["id"]


@pytest.mark.asyncio
async def test_products_sold_multi_unit_base_quantity(client, shop):
    h = shop["headers"]
    # Tạo đơn vị "thùng" rate 24 cho p1 (tồn 100 base đủ bán 2 thùng = 48)
    unit = (await client.post(
        f"/api/v1/products/{shop['p1']['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()
    # Bán 2 thùng theo đơn vị này
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "unit_id": unit["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(
        f"/api/v1/invoices/{inv['id']}/complete",
        json={"payments": [{"method": "CASH", "amount": float(inv["total"])}]},
        headers=h,
    )

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}", headers=h
    )
    item = r.json()["items"][0]
    # SL quy về đơn vị cơ bản: 2 thùng × 24 = 48
    assert float(item["quantity_sold"]) == 48
    # Giá vốn = cost_price(9000) × quantity(2) × rate(24) = 432000
    assert float(item["cost"]) == 432000


@pytest.mark.asyncio
async def test_products_sold_excludes_cancelled(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 4}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)
    await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "test"}, headers=h)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}", headers=h
    )
    assert len(r.json()["items"]) == 0


@pytest.mark.asyncio
async def test_products_sold_owner_only(client, shop):
    staff = await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0911777666", "password": "secret123",
    }, headers=shop["headers"])
    assert staff.status_code == 201
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0911777666", "password": "secret123",
    })).json()["access_token"]

    r = await client.get(
        "/api/v1/reports/products-sold", headers=_auth(cashier_token)
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_products_sold_invalid_sort(client, shop):
    r = await client.get(
        "/api/v1/reports/products-sold?sort_by=bogus", headers=shop["headers"]
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_report.py -k products_sold -v`
Expected: FAIL — endpoint chưa tồn tại (404, các assert sai). `test_products_sold_owner_only` có thể 404 thay vì 403.

- [ ] **Step 3: Commit (test đỏ)**

```bash
git add tests/test_report.py
git commit -m "test(report): add failing tests for products-sold report"
```

---

### Task 3: Backend — Service `products_sold` + endpoint

**Files:**
- Modify: `backend/modules/report/service.py` (thêm hàm + import Product)
- Modify: `backend/modules/report/router.py` (thêm endpoint + import schemas)

- [ ] **Step 1: Thêm import Product vào service**

Trong `backend/modules/report/service.py`, dòng import hiện có `from backend.modules.product.models import Product` — **đã có** (dùng cho stock). Xác nhận có; nếu chưa thì thêm. Không thêm trùng.

- [ ] **Step 2: Thêm hàm `products_sold` vào service**

Thêm vào cuối `backend/modules/report/service.py`:

```python
# ====================================================================
# Products sold (báo cáo SP đã bán) — phân trang + sort + lọc nhóm hàng
# ====================================================================

from math import ceil  # đặt ở đầu file cùng các import khác nếu chưa có


async def products_sold(
    db: AsyncSession,
    tenant_id: int,
    from_date: date,
    to_date: date,
    *,
    category_id: int | None = None,
    sort_by: str = "revenue",
    order: str = "desc",
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    if sort_by not in {"revenue", "quantity", "profit"}:
        sort_by = "revenue"
    if order not in {"asc", "desc"}:
        order = "desc"
    page = max(1, page)
    limit = max(1, min(limit, 100))

    start, end = _date_range(from_date, to_date)

    rate = func.coalesce(InvoiceItem.conversion_rate, 1)
    qty_base = func.sum(InvoiceItem.quantity * rate)
    gross = func.sum(InvoiceItem.unit_price * InvoiceItem.quantity)
    disc = func.sum(InvoiceItem.discount_amount)
    net = func.sum(InvoiceItem.line_total)
    cost = func.sum(InvoiceItem.cost_price * InvoiceItem.quantity * rate)

    filters = [
        Invoice.tenant_id == tenant_id,
        Invoice.status == "COMPLETED",
        Invoice.completed_at >= start,
        Invoice.completed_at < end,
    ]

    def _with_scope(stmt):
        stmt = stmt.join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        if category_id is not None:
            stmt = stmt.join(Product, Product.id == InvoiceItem.product_id).where(
                Product.category_id == category_id
            )
        return stmt.where(*filters)

    grouped = _with_scope(
        select(
            InvoiceItem.product_id.label("product_id"),
            InvoiceItem.product_sku.label("product_sku"),
            InvoiceItem.product_name.label("product_name"),
            qty_base.label("quantity_sold"),
            gross.label("revenue"),
            disc.label("discount"),
            net.label("net_revenue"),
            cost.label("cost"),
        )
    ).group_by(
        InvoiceItem.product_id,
        InvoiceItem.product_sku,
        InvoiceItem.product_name,
    )

    # Tổng số SP (distinct) khớp bộ lọc — count số nhóm
    total = (
        await db.execute(select(func.count()).select_from(grouped.subquery()))
    ).scalar() or 0

    # Totals trên TOÀN BỘ (không group, không phân trang)
    totals_row = (
        await db.execute(
            _with_scope(
                select(
                    func.coalesce(qty_base, 0),
                    func.coalesce(gross, 0),
                    func.coalesce(disc, 0),
                    func.coalesce(net, 0),
                    func.coalesce(cost, 0),
                )
            )
        )
    ).one()
    t_qty = Decimal(str(totals_row[0] or 0))
    t_gross = Decimal(str(totals_row[1] or 0))
    t_disc = Decimal(str(totals_row[2] or 0))
    t_net = Decimal(str(totals_row[3] or 0))
    t_cost = Decimal(str(totals_row[4] or 0))

    sort_exprs = {"revenue": net, "quantity": qty_base, "profit": net - cost}
    sort_col = sort_exprs[sort_by]
    direction = sort_col.desc() if order == "desc" else sort_col.asc()

    page_rows = (
        await db.execute(
            grouped.order_by(direction, InvoiceItem.product_id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()

    items = []
    for r in page_rows:
        revenue = Decimal(str(r.revenue or 0))
        discount = Decimal(str(r.discount or 0))
        net_revenue = Decimal(str(r.net_revenue or 0))
        c = Decimal(str(r.cost or 0))
        prof = net_revenue - c
        margin = (
            (prof / net_revenue * Decimal("100")).quantize(Decimal("0.01"))
            if net_revenue > 0
            else Decimal("0")
        )
        items.append(
            {
                "product_id": r.product_id,
                "product_sku": r.product_sku,
                "product_name": r.product_name,
                "quantity_sold": Decimal(str(r.quantity_sold or 0)),
                "revenue": revenue,
                "discount": discount,
                "net_revenue": net_revenue,
                "cost": c,
                "profit": prof,
                "margin_pct": margin,
            }
        )

    return {
        "from_date": from_date,
        "to_date": to_date,
        "sort_by": sort_by,
        "order": order,
        "category_id": category_id,
        "items": items,
        "totals": {
            "quantity_sold": t_qty,
            "revenue": t_gross,
            "discount": t_disc,
            "net_revenue": t_net,
            "cost": t_cost,
            "profit": t_net - t_cost,
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": int(total),
            "total_pages": int(ceil(total / limit)) if total else 0,
        },
    }
```

> Lưu ý: `from math import ceil` đặt lên cụm import đầu file (cạnh `from decimal import Decimal`). Không để import giữa file.

- [ ] **Step 3: Thêm endpoint vào router**

Trong `backend/modules/report/router.py`, thêm vào khối import schemas (dòng 13-21):

```python
from backend.modules.report.schemas import (
    DashboardResponse,
    ProductsSoldResponse,
    ProductsSoldSortBy,
    ProfitResponse,
    RevenuePoint,
    RevenueResponse,
    SortOrder,
    StockSummaryResponse,
    TopProductItem,
    TopProductsResponse,
)
```

Thêm endpoint mới (đặt sau `top_products`, trước `profit`):

```python
@router.get("/products-sold", response_model=ProductsSoldResponse)
async def products_sold(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    category_id: int | None = Query(default=None),
    sort_by: ProductsSoldSortBy = Query(default="revenue"),
    order: SortOrder = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    f, t = _default_range(from_date, to_date)
    data = await report_service.products_sold(
        db,
        owner.current_tenant_id,
        f,
        t,
        category_id=category_id,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )
    return ProductsSoldResponse(**data)
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `python -m pytest tests/test_report.py -k products_sold -v`
Expected: PASS toàn bộ 8 test products_sold.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/report/service.py backend/modules/report/router.py
git commit -m "feat(report): products-sold report endpoint (sort + paginate + category filter)"
```

---

### Task 4: Backend — Fix bug đơn vị quy đổi trong `top_products`

**Files:**
- Modify: `backend/modules/report/service.py` (hàm `top_products`, ~dòng 213-220)
- Modify: `tests/test_report.py` (thêm regression test)

`top_products` hiện cộng `SUM(quantity)` và `SUM(cost_price*quantity)` thiếu `conversion_rate` → sai SL & giá vốn cho hàng đa đơn vị.

- [ ] **Step 1: Thêm regression test (failing)**

Thêm vào `tests/test_report.py` (sau `test_top_products_excludes_cancelled`):

```python
@pytest.mark.asyncio
async def test_top_products_multi_unit(client, shop):
    h = shop["headers"]
    unit = (await client.post(
        f"/api/v1/products/{shop['p1']['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "unit_id": unit["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(
        f"/api/v1/invoices/{inv['id']}/complete",
        json={"payments": [{"method": "CASH", "amount": float(inv["total"])}]},
        headers=h,
    )

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/top-products?from={today}&to={today}", headers=h
    )
    item = r.json()["items"][0]
    # SL quy về cơ bản: 2 × 24 = 48 (trước fix là 2 → sai)
    assert float(item["quantity_sold"]) == 48
    # profit = net(2×288000) − cost(9000×2×24) = 576000 − 432000 = 144000
    assert float(item["profit"]) == 144000
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `python -m pytest tests/test_report.py::test_top_products_multi_unit -v`
Expected: FAIL — `quantity_sold` = 2 (chưa nhân rate), `profit` sai.

- [ ] **Step 3: Sửa `top_products`**

Trong `backend/modules/report/service.py`, hàm `top_products`, thay khối `select(...)` (dòng ~214-220) các biểu thức `qty` và `cost`:

```python
    rate = func.coalesce(InvoiceItem.conversion_rate, 1)
    q = await db.execute(
        select(
            InvoiceItem.product_id,
            InvoiceItem.product_sku,
            InvoiceItem.product_name,
            func.sum(InvoiceItem.quantity * rate).label("qty"),
            func.sum(InvoiceItem.line_total).label("revenue"),
            func.sum(InvoiceItem.cost_price * InvoiceItem.quantity * rate).label("cost"),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.completed_at >= start,
            Invoice.completed_at < end,
        )
        .group_by(
            InvoiceItem.product_id,
            InvoiceItem.product_sku,
            InvoiceItem.product_name,
        )
        .order_by(func.sum(InvoiceItem.line_total).desc())
        .limit(limit)
    )
```

(Chỉ đổi 2 dòng `func.sum(...qty...)` và `func.sum(...cost...)` để nhân `rate`; phần còn lại giữ nguyên.)

- [ ] **Step 4: Chạy lại test top-products (regression + cũ)**

Run: `python -m pytest tests/test_report.py -k top_products -v`
Expected: PASS — cả `test_top_products` (cũ, rate=1 nên không đổi), `test_top_products_excludes_cancelled`, `test_top_products_multi_unit`.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/report/service.py tests/test_report.py
git commit -m "fix(report): top-products quantity & cost must use conversion_rate"
```

---

### Task 5: Frontend — API client cho products-sold

**Files:**
- Modify: `frontend/src/api/report.ts`

- [ ] **Step 1: Thêm interfaces + hàm**

Thêm vào `frontend/src/api/report.ts` (sau khối `TopProductsResponse`, trước `ProfitResponse`):

```typescript
export type ProductsSoldSortBy = 'revenue' | 'quantity' | 'profit';
export type SortOrder = 'asc' | 'desc';

export interface ProductsSoldItem {
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity_sold: number | string;
  revenue: number | string;
  discount: number | string;
  net_revenue: number | string;
  cost: number | string;
  profit: number | string;
  margin_pct: number | string;
}

export interface ProductsSoldTotals {
  quantity_sold: number | string;
  revenue: number | string;
  discount: number | string;
  net_revenue: number | string;
  cost: number | string;
  profit: number | string;
}

export interface ProductsSoldPagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface ProductsSoldResponse {
  from_date: string;
  to_date: string;
  sort_by: ProductsSoldSortBy;
  order: SortOrder;
  category_id: number | null;
  items: ProductsSoldItem[];
  totals: ProductsSoldTotals;
  pagination: ProductsSoldPagination;
}

export interface ProductsSoldParams {
  from: string;
  to: string;
  category_id?: number;
  sort_by?: ProductsSoldSortBy;
  order?: SortOrder;
  page?: number;
  limit?: number;
}
```

Thêm hàm (sau `getTopProducts`):

```typescript
export async function getProductsSold(
  params: ProductsSoldParams,
): Promise<ProductsSoldResponse> {
  const { data } = await apiClient.get<ProductsSoldResponse>(
    '/reports/products-sold',
    { params },
  );
  return data;
}
```

- [ ] **Step 2: Verify tsc**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/report.ts
git commit -m "feat(report-fe): products-sold api client"
```

---

### Task 6: Frontend — MSW handler cho test

**Files:**
- Modify: `frontend/src/__tests__/mocks/handlers.ts`

- [ ] **Step 1: Thêm handler**

Thêm vào mảng handlers trong `frontend/src/__tests__/mocks/handlers.ts` (ngay sau handler `*/reports/top-products`, trước `*/reports/profit`):

```typescript
  http.get('*/reports/products-sold', ({ request }) => {
    const url = new URL(request.url);
    const from = url.searchParams.get('from') ?? '2026-05-01';
    const to = url.searchParams.get('to') ?? '2026-05-31';
    const page = Number(url.searchParams.get('page') ?? '1');
    return HttpResponse.json({
      from_date: from,
      to_date: to,
      sort_by: url.searchParams.get('sort_by') ?? 'revenue',
      order: url.searchParams.get('order') ?? 'desc',
      category_id: url.searchParams.get('category_id')
        ? Number(url.searchParams.get('category_id'))
        : null,
      items: [
        {
          product_id: 1,
          product_sku: 'SP000001',
          product_name: 'Mì tôm Hảo Hảo',
          quantity_sold: 120,
          revenue: 660000,
          discount: 60000,
          net_revenue: 600000,
          cost: 420000,
          profit: 180000,
          margin_pct: 30,
        },
        {
          product_id: 2,
          product_sku: 'SP000002',
          product_name: 'Coca 330ml',
          quantity_sold: 80,
          revenue: 560000,
          discount: 0,
          net_revenue: 560000,
          cost: 420000,
          profit: 140000,
          margin_pct: 25,
        },
      ],
      totals: {
        quantity_sold: 200,
        revenue: 1220000,
        discount: 60000,
        net_revenue: 1160000,
        cost: 840000,
        profit: 320000,
      },
      pagination: { page, limit: 20, total: 2, total_pages: 1 },
    });
  }),
```

Đảm bảo handler `*/categories` đã tồn tại (dropdown nhóm hàng dùng). Nếu chưa có, thêm:

```typescript
  http.get('*/categories', () =>
    HttpResponse.json({
      items: [
        { id: 1, name: 'Nước ngọt', depth: 1, sort_order: 0, children: [] },
      ],
    }),
  ),
```

> Trước khi thêm `*/categories`, grep file: nếu đã có thì BỎ QUA bước thêm category handler (tránh trùng).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/__tests__/mocks/handlers.ts
git commit -m "test(report-fe): msw handler for products-sold"
```

---

### Task 7: Frontend — Trang `ProductsSoldPage` + test

**Files:**
- Create: `frontend/src/pages/reports/ProductsSoldPage.tsx`
- Create: `frontend/src/pages/reports/__tests__/ProductsSoldPage.test.tsx`

- [ ] **Step 1: Viết test (failing)**

Tạo `frontend/src/pages/reports/__tests__/ProductsSoldPage.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProductsSoldPage from '../ProductsSoldPage';

describe('ProductsSoldPage', () => {
  it('renders product rows with full columns + totals', async () => {
    render(
      <MemoryRouter>
        <ProductsSoldPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText('Sản phẩm đã bán'),
    ).toBeInTheDocument();
    expect(await screen.findByText('SP000001')).toBeInTheDocument();
    expect(screen.getAllByText('Mì tôm Hảo Hảo').length).toBeGreaterThan(0);
    // doanh thu thuần p1 = 600.000
    expect(screen.getByText('600.000 VNĐ')).toBeInTheDocument();
    // dòng tổng cộng — doanh thu thuần tổng = 1.160.000
    expect(screen.getByText('Tổng cộng')).toBeInTheDocument();
    expect(screen.getByText('1.160.000 VNĐ')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `cd frontend && npx vitest run src/pages/reports/__tests__/ProductsSoldPage.test.tsx`
Expected: FAIL — module `ProductsSoldPage` chưa tồn tại.

- [ ] **Step 3: Tạo trang**

Tạo `frontend/src/pages/reports/ProductsSoldPage.tsx`:

```tsx
import { useCallback, useEffect, useState } from 'react';
import dayjs from 'dayjs';
import DateRangePicker, {
  type DateRange,
} from '../../components/DateRangePicker';
import * as reportApi from '../../api/report';
import type {
  ProductsSoldResponse,
  ProductsSoldSortBy,
  SortOrder,
} from '../../api/report';
import { listCategories, type CategoryNode } from '../../api/category';
import { formatVND, formatQty } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

interface CatOption {
  id: number;
  label: string;
}

function flatten(nodes: CategoryNode[], depth = 0): CatOption[] {
  const out: CatOption[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, label: `${'— '.repeat(depth)}${n.name}` });
    if (n.children?.length) out.push(...flatten(n.children, depth + 1));
  }
  return out;
}

const SORT_OPTIONS: { value: ProductsSoldSortBy; label: string }[] = [
  { value: 'revenue', label: 'Doanh thu thuần' },
  { value: 'quantity', label: 'Số lượng bán' },
  { value: 'profit', label: 'Lợi nhuận gộp' },
];

export default function ProductsSoldPage() {
  const [range, setRange] = useState<DateRange>(() => {
    const today = dayjs().format('YYYY-MM-DD');
    return { from: today, to: today };
  });
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [sortBy, setSortBy] = useState<ProductsSoldSortBy>('revenue');
  const [order, setOrder] = useState<SortOrder>('desc');
  const [page, setPage] = useState(1);
  const [cats, setCats] = useState<CatOption[]>([]);
  const [data, setData] = useState<ProductsSoldResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listCategories()
      .then((res) => setCats(flatten(res.items)))
      .catch(() => setCats([]));
  }, []);

  const fetchData = useCallback(
    async (
      r: DateRange,
      cat: number | '',
      sb: ProductsSoldSortBy,
      ord: SortOrder,
      pg: number,
    ) => {
      setLoading(true);
      setError(null);
      try {
        const res = await reportApi.getProductsSold({
          from: r.from,
          to: r.to,
          ...(cat ? { category_id: cat } : {}),
          sort_by: sb,
          order: ord,
          page: pg,
          limit: 20,
        });
        setData(res);
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void fetchData(range, categoryId, sortBy, order, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, order, page]);

  const onSubmit = () => {
    if (range.from && range.to && range.from > range.to) return;
    setPage(1);
    void fetchData(range, categoryId, sortBy, order, 1);
  };

  const toggleSort = (col: ProductsSoldSortBy) => {
    if (sortBy === col) {
      setOrder((o) => (o === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(col);
      setOrder('desc');
    }
    setPage(1);
  };

  const sortArrow = (col: ProductsSoldSortBy) =>
    sortBy === col ? (order === 'desc' ? ' ▼' : ' ▲') : '';

  const items = data?.items ?? [];
  const totals = data?.totals;
  const pag = data?.pagination;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Sản phẩm đã bán</h1>

      <div className="flex flex-wrap items-end gap-3">
        <DateRangePicker value={range} onChange={setRange} />
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Nhóm hàng</span>
          <select
            aria-label="Nhóm hàng"
            value={categoryId}
            onChange={(e) =>
              setCategoryId(e.target.value ? Number(e.target.value) : '')
            }
            className="border border-slate-300 rounded px-2 py-1"
          >
            <option value="">Tất cả nhóm hàng</option>
            {cats.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Sắp xếp theo</span>
          <select
            aria-label="Sắp xếp theo"
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as ProductsSoldSortBy);
              setPage(1);
            }}
            className="border border-slate-300 rounded px-2 py-1"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={onSubmit}
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          Xem báo cáo
        </button>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded overflow-x-auto">
        {loading ? (
          <div className="p-4">
            <SkeletonCard />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">SKU</th>
                <th className="px-3 py-2 text-left">Tên sản phẩm</th>
                <th
                  className="px-3 py-2 text-right cursor-pointer select-none"
                  onClick={() => toggleSort('quantity')}
                >
                  SL bán{sortArrow('quantity')}
                </th>
                <th className="px-3 py-2 text-right">Doanh thu</th>
                <th className="px-3 py-2 text-right">Giảm giá</th>
                <th
                  className="px-3 py-2 text-right cursor-pointer select-none"
                  onClick={() => toggleSort('revenue')}
                >
                  Doanh thu thuần{sortArrow('revenue')}
                </th>
                <th className="px-3 py-2 text-right">Giá vốn</th>
                <th
                  className="px-3 py-2 text-right cursor-pointer select-none"
                  onClick={() => toggleSort('profit')}
                >
                  Lợi nhuận gộp{sortArrow('profit')}
                </th>
                <th className="px-3 py-2 text-right">Tỷ suất %</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-3 py-6">
                    <EmptyState title="Không có sản phẩm nào bán ra trong kỳ" />
                  </td>
                </tr>
              ) : (
                items.map((it) => (
                  <tr key={it.product_id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">
                      {it.product_sku}
                    </td>
                    <td className="px-3 py-2">{it.product_name}</td>
                    <td className="px-3 py-2 text-right">
                      {formatQty(it.quantity_sold as number)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.revenue)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.discount)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.net_revenue)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.cost)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(it.profit)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {Number(it.margin_pct).toFixed(1)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            {totals && items.length > 0 && (
              <tfoot className="bg-slate-50 font-semibold border-t-2 border-slate-300">
                <tr>
                  <td className="px-3 py-2" colSpan={2}>
                    Tổng cộng
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatQty(totals.quantity_sold as number)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.revenue)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.discount)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.net_revenue)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.cost)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {formatVND(totals.profit)}
                  </td>
                  <td className="px-3 py-2" />
                </tr>
              </tfoot>
            )}
          </table>
        )}
      </div>

      {pag && pag.total_pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
          >
            Trước
          </button>
          <span>
            Trang {pag.page}/{pag.total_pages}
          </span>
          <button
            disabled={page >= pag.total_pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 border border-slate-300 rounded disabled:opacity-40"
          >
            Sau
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `cd frontend && npx vitest run src/pages/reports/__tests__/ProductsSoldPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/reports/ProductsSoldPage.tsx frontend/src/pages/reports/__tests__/ProductsSoldPage.test.tsx
git commit -m "feat(report-fe): products-sold page (sortable cols, pagination, totals)"
```

---

### Task 8: Frontend — Wire route + nav

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: Thêm lazy import + route (OWNER-only) trong App.tsx**

Sau dòng `const TopProductsPage = lazy(...)` (dòng 34) thêm:

```tsx
const ProductsSoldPage = lazy(() => import('./pages/reports/ProductsSoldPage'));
```

Trong khối routes, sau route `/reports/top-products` (dòng 128-131) thêm:

```tsx
                <Route
                  path="/reports/products-sold"
                  element={
                    <OwnerOnly>
                      <ProductsSoldPage />
                    </OwnerOnly>
                  }
                />
```

- [ ] **Step 2: Thêm nav item (OWNER section) trong AppLayout.tsx**

Trong `frontend/src/components/AppLayout.tsx`, mảng owner-only (dòng 156-161), thêm vào đầu danh sách owner:

```tsx
          { to: '/reports/products-sold', label: 'SP đã bán', icon: icons.topProducts },
```

(Dùng lại `icons.topProducts` cho gọn — không cần icon mới.)

- [ ] **Step 3: Verify tsc + chạy full FE suite**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: tsc exit 0; toàn bộ test pass (kể cả test cũ + ProductsSoldPage mới).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/AppLayout.tsx
git commit -m "feat(report-fe): mount products-sold route + nav (owner-only)"
```

---

### Task 9: Verify toàn hệ thống

- [ ] **Step 1: Backend full suite**

Run: `python -m pytest tests/ -q`
Expected: tất cả pass (không regression ở các module khác).

- [ ] **Step 2: Frontend full suite + typecheck**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: tsc exit 0; toàn bộ test pass.

- [ ] **Step 3: Commit cuối (nếu còn thay đổi lẻ)**

```bash
git add -A
git commit -m "chore(report): products-sold feature complete" || echo "nothing to commit"
```

---

## Self-Review

**1. Spec coverage:**
- Chọn from/to mặc định hôm nay → endpoint dùng `_default_range` (mặc định 30 ngày gần nhất; FE `defaultRangeLast30`). ⚠️ Lưu ý: spec gốc nói "mặc định hôm nay" nhưng `_default_range` hiện trả 30 ngày. Quyết định: giữ 30 ngày cho nhất quán với các report khác; nếu user muốn đúng "hôm nay" → đổi default ở FE state thành `{from: today, to: today}` (1 dòng). Đã ghi để hỏi lại nếu cần. ✅ Liệt kê tất cả SP (Task 3, bỏ limit top-N). ✅ SL/doanh thu/lợi nhuận (Task 1/3). ✅ Sort (Task 3, sort_by/order). ✅ Phân trang (Task 3). ✅ Lọc nhóm hàng (Task 3). ✅ Trang FE (Task 7-8). ✅ Fix top_products (Task 4). ✅ OWNER-only (Task 3 router). ✅ Cột đầy đủ KiotViet + dòng tổng (Task 7). ✅ Tiếng Việt toàn bộ label (Task 7).
- **Migration checklist CLAUDE.md:** không cần migration (read-only). Mọi query lọc `tenant_id` ✅. Không mutation → không cần audit/price_history/require_role mutation. Endpoint `require_role("OWNER")` ✅. Test tenant isolation: dashboard đã có `test_report_tenant_isolation`; products-sold dùng cùng `tenant_id` filter pattern — an toàn (có thể thêm test isolation riêng nếu muốn, nhưng pattern giống hệt đã được cover).

**2. Placeholder scan:** Không có TBD/TODO; mọi step có code/command + expected output cụ thể.

**3. Type consistency:** `products_sold` service trả dict khớp `ProductsSoldResponse(**data)` (keys: from_date,to_date,sort_by,order,category_id,items,totals,pagination). `ProductsSoldItem` fields khớp dict items. `ProductsSoldSortBy`/`SortOrder` import vào router để type query param. FE interfaces khớp JSON backend. `getProductsSold` params khớp query backend (`from`,`to`,`category_id`,`sort_by`,`order`,`page`,`limit`).

**Điểm cần xác nhận lại với user ở Gate 2:** default range (hôm nay vs 30 ngày) — xem mục Spec coverage #1.
