# Badge cảnh báo tồn kho trong danh sách Sản phẩm — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hiện badge "Hết"/"Sắp hết" cạnh tên sản phẩm trong danh sách Sản phẩm (`ProductListScreen`), dựa trên 1 field mới `stock_status` mà backend tính sẵn trong response của `GET /products`.

**Architecture:** Backend (`product/service.py`) truy vấn thêm tồn kho hiện tại cho các SP trong trang kết quả (1 query `IN (...)`, không N+1), phân loại theo đúng quy tắc đã dùng ở Báo cáo (`min_stock=0` → bỏ qua; tồn ≤0 → OUT; tồn ≤ min_stock → LOW), gắn vào `ProductResponse.stock_status` (field mới, optional, mặc định `None` — không ảnh hưởng các endpoint khác dùng chung schema). Android chỉ cần thêm field vào DTO và render badge có sẵn (`MonoBadge`, tái dùng string `inv_badge_out`/`inv_badge_low` đã có ở màn Tồn kho).

**Tech Stack:** Backend: Python/FastAPI/SQLAlchemy async/pytest. Android: Kotlin/Compose/kotlinx.serialization.

## Global Constraints

- Chỉ `GET /products` (danh sách) tính `stock_status` thật; các endpoint chi tiết/tạo/sửa SP (`_to_product_response` gọi không truyền `stock_status`) giữ nguyên, luôn `None`.
- Sản phẩm có `min_stock = 0` không bao giờ được đánh dấu OUT/LOW.
- Không đổi màn chi tiết SP, tạo mới, sửa SP, hay màn Tồn kho.
- Không đổi màu sắc/theme.
- Mọi text hiển thị tiếng Việt — tái dùng `R.string.inv_badge_out`/`inv_badge_low` đã có (không tạo string trùng nghĩa).
- Chạy lệnh Android từ `android/`: `./gradlew :app:compileDebugKotlin`, `./gradlew :app:testDebugUnitTest`.
- Chạy test backend từ thư mục gốc repo bằng venv có sẵn: `.venv/Scripts/python.exe -m pytest tests/test_product.py -v`.
- Commit message tiếng Việt, kết thúc bằng: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Backend — `stock_status` trong `GET /products`

**Files:**
- Modify: `backend/modules/product/schemas.py`
- Modify: `backend/modules/product/service.py`
- Modify: `backend/modules/product/router.py`
- Test: `tests/test_product.py`

**Interfaces:**
- Produces: `ProductResponse.stock_status: Literal["OUT", "LOW"] | None = None`; `list_products()` trả thêm key `stock_by_id: dict[int, str | None]` trong dict kết quả; `_to_product_response(p, user, stock_status=None)` — tham số mới tùy chọn.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/test_product.py` (dùng đúng `_auth`, `registered_owner` đã có sẵn trong file):

```python
@pytest.mark.asyncio
async def test_list_products_stock_status_low(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Sắp Hết", "sale_price": 10000, "min_stock": 5,
    }, headers=h)).json()
    # supplier_id BẮT BUỘC ở đây: complete goods-receipt với paid_amount=0 (mặc định)
    # và không có supplier_id sẽ bị chặn bởi rule DEBT_REQUIRES_SUPPLIER (400).
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC Test"}, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [{"product_id": p["id"], "quantity": 3, "cost_price": 5000}],
    }, headers=h)).json()
    complete = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert complete.status_code == 200, complete.text

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] == "LOW"


@pytest.mark.asyncio
async def test_list_products_stock_status_out_never_stocked(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Chưa Nhập", "sale_price": 10000, "min_stock": 5,
    }, headers=h)).json()

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] == "OUT"


@pytest.mark.asyncio
async def test_list_products_stock_status_none_when_min_stock_zero(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Không Ngưỡng", "sale_price": 10000,
    }, headers=h)).json()

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] is None


@pytest.mark.asyncio
async def test_list_products_stock_status_none_when_sufficient(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Đủ Hàng", "sale_price": 10000, "min_stock": 5,
    }, headers=h)).json()
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC Test"}, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [{"product_id": p["id"], "quantity": 100, "cost_price": 5000}],
    }, headers=h)).json()
    complete = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert complete.status_code == 200, complete.text

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] is None
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run (từ thư mục gốc repo): `.venv/Scripts/python.exe -m pytest tests/test_product.py -k stock_status -v`
Expected: FAIL (`KeyError: 'stock_status'` — field chưa tồn tại trong response).

- [ ] **Step 3: Thêm field vào schema**

Trong `backend/modules/product/schemas.py`, class `ProductResponse` (đã có `import Literal` sẵn ở đầu file), thêm field cuối cùng trước `model_config`:

```python
    stock_status: Literal["OUT", "LOW"] | None = None
```

- [ ] **Step 4: Thêm hàm phân loại + sửa `list_products()`**

Trong `backend/modules/product/service.py`, thêm import `Inventory`:

```python
from backend.modules.inventory.models import Inventory
```

Thêm hàm thuần ngay trước `async def list_products(...)`:

```python
def _classify_stock(quantity, min_stock: int) -> str | None:
    """Phân loại tồn kho cho 1 sản phẩm. min_stock<=0 → không cảnh báo (đúng quy tắc
    đã dùng ở report_service._low_stock_counts: chỉ cảnh báo khi min_stock > 0)."""
    if min_stock <= 0:
        return None
    if quantity is None or quantity <= 0:
        return "OUT"
    if quantity <= min_stock:
        return "LOW"
    return None
```

Trong `list_products()`, thay dòng cuối cùng `return await paginate(db, stmt, page=page, limit=limit)` bằng:

```python
    result = await paginate(db, stmt, page=page, limit=limit)

    product_ids = [p.id for p in result["items"]]
    stock_by_id: dict[int, str | None] = {}
    if product_ids:
        qty_rows = await db.execute(
            select(Inventory.product_id, Inventory.quantity).where(
                Inventory.tenant_id == tenant_id,
                Inventory.product_id.in_(product_ids),
            )
        )
        qty_by_id = {pid: qty for pid, qty in qty_rows.all()}
        for p in result["items"]:
            stock_by_id[p.id] = _classify_stock(qty_by_id.get(p.id), p.min_stock)

    result["stock_by_id"] = stock_by_id
    return result
```

- [ ] **Step 5: Sửa router**

Trong `backend/modules/product/router.py`, sửa hàm `_to_product_response`:

```python
def _to_product_response(p, user: User, stock_status: str | None = None) -> ProductResponse:
    show_cost = can_see_cost(getattr(user, "_tenant", None), user.role)
    data = {
        "id": p.id,
        "sku": p.sku,
        "barcode": p.barcode,
        "name": p.name,
        "description": p.description,
        "unit": p.unit,
        "cost_price": p.cost_price if show_cost else None,
        "sale_price": p.sale_price,
        "min_stock": p.min_stock,
        "image_url": p.image_url,
        "status": p.status,
        "allow_negative": p.allow_negative,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "units": [ProductUnitResponse.model_validate(u) for u in (p.units or [])],
        "stock_status": stock_status,
    }
    return ProductResponse(**data)
```

Sửa endpoint `list_products` (route `GET ""`), thay:

```python
    return ProductListResponse(
        items=[_to_product_response(p, user) for p in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )
```

thành:

```python
    return ProductListResponse(
        items=[
            _to_product_response(p, user, stock_status=result["stock_by_id"].get(p.id))
            for p in result["items"]
        ],
        pagination=Pagination(**result["pagination"]),
    )
```

Các call site khác của `_to_product_response(product, user)` (detail/create/update) **giữ nguyên không đổi** — dùng mặc định `stock_status=None`.

- [ ] **Step 6: Chạy lại test — kỳ vọng PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_product.py -v`
Expected: PASS toàn bộ (bao gồm 4 test `stock_status` mới VÀ toàn bộ test cũ trong file — xác nhận không phá hành vi hiện có).

- [ ] **Step 7: Commit**

```bash
git add backend/modules/product/schemas.py backend/modules/product/service.py backend/modules/product/router.py tests/test_product.py
git commit -m "feat(product): thêm stock_status vào GET /products cho badge tồn kho

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Android — DTO + badge trong danh sách Sản phẩm

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/dto/ProductDtos.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/ProductListScreen.kt`

**Interfaces:**
- Consumes: field `stock_status` từ Task 1 (giá trị `"OUT"` | `"LOW"` | `null`); `MonoBadge(text: String, modifier: Modifier = Modifier, filled: Boolean = true)` và `R.string.inv_badge_out`/`inv_badge_low` (đã có sẵn trong dự án, không cần tạo mới).

- [ ] **Step 1: Thêm field vào DTO**

Trong `ProductDtos.kt`, class `ProductBriefDto`, thêm field cuối cùng (trước dấu đóng ngoặc):

```kotlin
    @SerialName("stock_status") val stockStatus: String? = null,
```

- [ ] **Step 2: Thêm badge vào `ProductListCard`**

Nội dung hiện tại của khối này (trong hàm `ProductListCard`, bên trong `Row(verticalAlignment = Alignment.CenterVertically) { ... }` chứa tên SP) là:

```kotlin
                    if (product.status == "INACTIVE") {
                        Spacer(Modifier.width(6.dp))
                        MonoBadge(stringResource(R.string.cat_product_status_inactive_short), filled = false)
                    }
                }
```

Sửa thành (thêm khối `when` mới làm câu lệnh TIẾP THEO, SAU khi khối `if` đã đóng — là 1 statement cùng cấp với `if`, KHÔNG lồng vào bên trong `if`):

```kotlin
                    if (product.status == "INACTIVE") {
                        Spacer(Modifier.width(6.dp))
                        MonoBadge(stringResource(R.string.cat_product_status_inactive_short), filled = false)
                    }
                    when (product.stockStatus) {
                        "OUT" -> {
                            Spacer(Modifier.width(6.dp))
                            MonoBadge(stringResource(R.string.inv_badge_out), filled = true)
                        }
                        "LOW" -> {
                            Spacer(Modifier.width(6.dp))
                            MonoBadge(stringResource(R.string.inv_badge_low), filled = false)
                        }
                        else -> {}
                    }
                }
```

Lưu ý: dấu `}` cuối cùng ở trên đóng `Row(verticalAlignment = Alignment.CenterVertically) { ... }` bao ngoài — khối `when` mới phải nằm NGANG HÀNG với khối `if`, không phải bên trong nó (nếu đặt nhầm vào trong `if`, badge tồn kho sẽ chỉ hiện khi SP đồng thời bị Ngừng bán — SAI). Không cần thêm import — `MonoBadge`, `stringResource`, `Modifier`, `Spacer` đã được import sẵn trong file (badge INACTIVE đã dùng chung các API này).

- [ ] **Step 3: Compile**

Run (từ `android/`): `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Chạy toàn bộ unit test**

Run: `./gradlew :app:testDebugUnitTest`
Expected: PASS toàn bộ (không có test nào liên quan trực tiếp tới thay đổi này bị ảnh hưởng — đây là binding UI đơn giản, giống cách badge INACTIVE hiện có không có test riêng).

- [ ] **Step 5: Rà soát trực quan**

Chạy app, mở màn Sản phẩm: SP có `min_stock>0` và tồn ≤0 hiện badge "Hết" (đậm); SP có tồn ≤ min_stock nhưng >0 hiện badge "Sắp hết" (nhạt); SP đủ hàng hoặc `min_stock=0` không có badge. SP vừa "Ngừng bán" vừa sắp/hết hàng hiện cả 2 badge cạnh nhau.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/dto/ProductDtos.kt android/app/src/main/java/com/mykiot/pos/feature/product/ProductListScreen.kt
git commit -m "feat(product): hiện badge Hết/Sắp hết trong danh sách sản phẩm

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (đã thực hiện khi viết plan)

- **Spec coverage:** mục 3.1-3.3 (field + tính toán + router) → Task 1; mục 3.4 (test) → Task 1; mục 4.1-4.2 (DTO + UI) → Task 2; mục 2 (2 trạng thái Hết/Sắp hết, badge trên từng dòng) → Task 2.
- **Placeholder scan:** không có TBD/TODO; mọi step có code/lệnh cụ thể; đã xác nhận trước `Literal` đã import sẵn trong `schemas.py` và `supplier_id` là optional ở `GoodsReceiptCreateRequest` (không cần tạo NCC trong test).
- **Type consistency:** `stock_status: Literal["OUT", "LOW"] | None` (Python) ↔ `stockStatus: String?` (Kotlin) dùng nhất quán ở cả 2 task; `_classify_stock(quantity, min_stock)` chỉ dùng nội bộ Task 1, không lộ ra interface nào task khác cần biết ngoài field JSON cuối cùng.
