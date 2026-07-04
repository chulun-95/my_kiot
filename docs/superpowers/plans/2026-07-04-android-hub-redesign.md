# Sắp xếp lại Hub Android + card có số liệu thật — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sắp xếp lại màn Hub (trang chủ) Android thành 3 nhóm mới với card thu nhỏ có dòng số liệu thật, dòng chào theo vai trò, và menu Cài đặt (Đổi mật khẩu + Đăng xuất) thay cho nút Đăng xuất, dựa trên 1 endpoint backend mới đếm tổng hợp.

**Architecture:** Backend thêm 1 endpoint `GET /reports/hub-summary` (module `report`, tái dùng logic đếm sắp/hết hàng đã có). Android thêm DTO/API/Repository tương ứng, 1 hàm thuần `captionFor()` chọn caption (số thật hoặc tĩnh) có thể unit-test bằng `FakeResProvider`, `HubViewModel` gọi API và tính sẵn map caption theo route, `HubScreen` chỉ đọc caption có sẵn từ state — không tự tính chuỗi tài nguyên (giữ đúng quy ước dự án: `ResProvider` chỉ dùng ở tầng không phải Composable).

**Tech Stack:** Backend: Python/FastAPI/SQLAlchemy async/pytest. Android: Kotlin/Compose/Hilt/Retrofit/kotlinx.serialization/JUnit+mockk.

## Global Constraints

- Mọi text hiển thị cho người dùng PHẢI tiếng Việt (theo CLAUDE.md) — dùng `stringResource`/`ResProvider.get`, không hardcode.
- Mọi query backend BẮT BUỘC filter theo `tenant_id` của user hiện tại (`user.current_tenant_id`), không nhận tenant_id từ request.
- Response format theo chuẩn dự án: object đơn (không phân trang) cho `hub-summary`.
- Không đổi route/navigation của bất kỳ card nào; không đổi màn đích.
- Không đổi màu sắc/theme (giữ đơn sắc hiện tại).
- Nếu API `hub-summary` lỗi → card rơi về caption tĩnh, KHÔNG hiện `ErrorDialog`.
- Chạy lệnh Android từ thư mục `android/`: `./gradlew :app:compileDebugKotlin`, `./gradlew :app:testDebugUnitTest`.
- Chạy test backend từ thư mục gốc repo: `python -m pytest tests/test_report.py -v` (dùng `.venv/Scripts/python.exe` nếu có venv, xem Task 1).
- Commit message tiếng Việt, kết thúc bằng: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Backend — endpoint `GET /reports/hub-summary`

**Files:**
- Modify: `backend/modules/report/schemas.py`
- Modify: `backend/modules/report/service.py`
- Modify: `backend/modules/report/router.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Produces: `HubSummaryResponse` (Pydantic), `report_service.hub_summary(db, tenant_id) -> dict[str, Any]` trả 6 key: `total_products`, `low_stock_count`, `out_of_stock_count`, `total_customers`, `total_suppliers`, `draft_receipts_count`. Route: `GET /api/v1/reports/hub-summary`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/test_report.py`:

```python
# ===================================================================
# Hub Summary
# ===================================================================

@pytest.mark.asyncio
async def test_hub_summary_basic_counts(client, shop):
    h = shop["headers"]
    r = await client.get("/api/v1/reports/hub-summary", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_products"] == 2          # p1, p2 từ fixture shop
    assert body["total_suppliers"] == 1          # NCC Test từ fixture shop
    assert body["total_customers"] == 0
    assert body["draft_receipts_count"] == 0     # phiếu nhập trong fixture đã complete
    assert body["low_stock_count"] == 0
    assert body["out_of_stock_count"] == 0


@pytest.mark.asyncio
async def test_hub_summary_counts_draft_receipt(client, shop):
    h = shop["headers"]
    # Tạo thêm 1 phiếu nhập KHÔNG complete → vẫn ở DRAFT
    await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000}],
    }, headers=h)

    r = await client.get("/api/v1/reports/hub-summary", headers=h)
    body = r.json()
    assert body["draft_receipts_count"] == 1


@pytest.mark.asyncio
async def test_hub_summary_low_and_out_of_stock(client, shop):
    h = shop["headers"]
    # p1 min_stock=5, tồn ban đầu 100. Bán 96 → tồn 4 (<5) → LOW, chưa OUT.
    await _complete_invoice(client, h, shop["p1"]["id"], 96)
    r = await client.get("/api/v1/reports/hub-summary", headers=h)
    body = r.json()
    assert body["low_stock_count"] >= 1
    assert body["out_of_stock_count"] == 0

    # Bán nốt 4 còn lại → tồn 0 → OUT_OF_STOCK.
    await _complete_invoice(client, h, shop["p1"]["id"], 4)
    r2 = await client.get("/api/v1/reports/hub-summary", headers=h)
    body2 = r2.json()
    assert body2["out_of_stock_count"] >= 1


@pytest.mark.asyncio
async def test_hub_summary_tenant_isolation(client):
    """Tenant A không thấy số liệu tenant B."""
    a = (await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "owner_name": "OA",
        "phone": "0903111111", "password": "secret123",
    })).json()
    b = (await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "owner_name": "OB",
        "phone": "0903222222", "password": "secret123",
    })).json()
    h_a = _auth(a["access_token"])
    h_b = _auth(b["access_token"])

    # Shop A tạo 2 SP + 1 KH; Shop B không tạo gì.
    await client.post("/api/v1/products", json={
        "name": "PA1", "sku": "PA1", "sale_price": 1000,
    }, headers=h_a)
    await client.post("/api/v1/products", json={
        "name": "PA2", "sku": "PA2", "sale_price": 1000,
    }, headers=h_a)
    await client.post("/api/v1/customers", json={"name": "KH A"}, headers=h_a)

    body_a = (await client.get("/api/v1/reports/hub-summary", headers=h_a)).json()
    body_b = (await client.get("/api/v1/reports/hub-summary", headers=h_b)).json()

    assert body_a["total_products"] == 2
    assert body_a["total_customers"] == 1
    assert body_b["total_products"] == 0
    assert body_b["total_customers"] == 0


@pytest.mark.asyncio
async def test_hub_summary_requires_auth(client):
    r = await client.get("/api/v1/reports/hub-summary")
    assert r.status_code == 401
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run (từ thư mục gốc repo, dùng venv có sẵn):
`.venv/Scripts/python.exe -m pytest tests/test_report.py -k hub_summary -v`
Expected: FAIL (404 Not Found — route chưa tồn tại).

- [ ] **Step 3: Thêm schema**

Trong `backend/modules/report/schemas.py`, chèn ngay sau class `DashboardResponse` (trước `# ---------- Revenue ----------`):

```python
class HubSummaryResponse(BaseModel):
    total_products: int
    low_stock_count: int       # gồm cả OUT_OF_STOCK + LOW (giống dashboard)
    out_of_stock_count: int    # subset của low_stock_count: tồn ≤ 0
    total_customers: int
    total_suppliers: int
    draft_receipts_count: int
```

- [ ] **Step 4: Tách hàm dùng chung + thêm service function**

Trong `backend/modules/report/service.py`, thay khối tính low-stock hiện có trong `dashboard()` (đoạn từ `# Low stock — tách ra...` tới `low_stock_count = len(low_rows)`) bằng lời gọi hàm dùng chung mới. Trước hết, thêm hàm mới **ngay trước** `async def dashboard(...)`:

```python
async def _low_stock_counts(db: AsyncSession, tenant_id: int) -> tuple[int, int]:
    """Trả (low_stock_count, out_of_stock_count). low_stock_count gồm cả out_of_stock.
    Anchor trên Product + LEFT JOIN Inventory: SP chưa từng nhập kho vẫn tính hết hàng."""
    qty_col = func.coalesce(Inventory.quantity, 0)
    low_q = await db.execute(
        select(qty_col)
        .select_from(Product)
        .outerjoin(
            Inventory,
            (Inventory.product_id == Product.id)
            & (Inventory.tenant_id == tenant_id),
        )
        .where(
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
            Product.status == "ACTIVE",
            Product.min_stock > 0,
            qty_col <= Product.min_stock,
        )
    )
    low_rows = low_q.all()
    out_of_stock_count = sum(1 for (q,) in low_rows if (q or 0) <= 0)
    low_stock_count = len(low_rows)
    return low_stock_count, out_of_stock_count
```

Sau đó, trong `dashboard()`, thay toàn bộ khối (từ comment `# Low stock — tách ra...` tới dòng `low_stock_count = len(low_rows)`) bằng:

```python
    low_stock_count, out_of_stock_count = await _low_stock_counts(db, tenant_id)
```

(Giữ nguyên phần còn lại của `dashboard()` — comment cũ, biến `qty_col`, `low_q`, `low_rows` không còn dùng ở đây nữa vì đã chuyển vào hàm dùng chung.)

Cuối file (sau hàm `dashboard`, trước `# ====================================================================\n# Revenue`), thêm:

```python
# ====================================================================
# Hub Summary
# ====================================================================

async def hub_summary(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    low_stock_count, out_of_stock_count = await _low_stock_counts(db, tenant_id)

    total_products = int(
        (await db.execute(
            select(func.count(Product.id)).where(
                Product.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
                Product.status == "ACTIVE",
            )
        )).scalar() or 0
    )
    total_customers = int(
        (await db.execute(
            select(func.count(Customer.id)).where(
                Customer.tenant_id == tenant_id,
                Customer.deleted_at.is_(None),
            )
        )).scalar() or 0
    )
    total_suppliers = int(
        (await db.execute(
            select(func.count(Supplier.id)).where(
                Supplier.tenant_id == tenant_id,
                Supplier.deleted_at.is_(None),
            )
        )).scalar() or 0
    )
    draft_receipts_count = int(
        (await db.execute(
            select(func.count(GoodsReceipt.id)).where(
                GoodsReceipt.tenant_id == tenant_id,
                GoodsReceipt.status == "DRAFT",
            )
        )).scalar() or 0
    )

    return {
        "total_products": total_products,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_customers": total_customers,
        "total_suppliers": total_suppliers,
        "draft_receipts_count": draft_receipts_count,
    }
```

- [ ] **Step 5: Thêm route**

Trong `backend/modules/report/router.py`, sửa import block: thêm `HubSummaryResponse` vào danh sách import từ `backend.modules.report.schemas` (chèn sau `EndOfDayResponse`, trước `ProductsSoldResponse`):

```python
from backend.modules.report.schemas import (
    DashboardResponse,
    DebtItem,
    DebtReportResponse,
    EodMethodRow,
    EndOfDayResponse,
    HubSummaryResponse,
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

Thêm route mới ngay sau hàm `dashboard(...)` (sau dòng `return DashboardResponse(**data)`):

```python
@router.get("/hub-summary", response_model=HubSummaryResponse)
async def hub_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    data = await report_service.hub_summary(db, user.current_tenant_id)
    return HubSummaryResponse(**data)
```

- [ ] **Step 6: Chạy lại test — kỳ vọng PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_report.py -v`
Expected: PASS toàn bộ (bao gồm các test `dashboard` cũ — xác nhận refactor `_low_stock_counts` không phá vỡ hành vi cũ — và các test `hub_summary` mới).

- [ ] **Step 7: Commit**

```bash
git add backend/modules/report/schemas.py backend/modules/report/service.py backend/modules/report/router.py tests/test_report.py
git commit -m "feat(report): thêm endpoint GET /reports/hub-summary đếm tổng hợp cho Hub

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Android — DTO + API + Repository cho hub-summary

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/dto/ReportDtos.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/ReportApi.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/report/data/ReportRepository.kt`

**Interfaces:**
- Consumes: response JSON từ Task 1 (`GET /reports/hub-summary`).
- Produces: `HubSummaryDto` (6 field), `ReportApi.hubSummary(): HubSummaryDto`, `ReportRepository.hubSummary(): ApiResult<HubSummaryDto>` — Task 5 sẽ dùng trực tiếp các API này.

- [ ] **Step 1: Thêm DTO**

Trong `ReportDtos.kt`, chèn ngay sau `DashboardDto` (trước `EodMethodRowDto`):

```kotlin
@Serializable
data class HubSummaryDto(
    @SerialName("total_products") val totalProducts: Int,
    @SerialName("low_stock_count") val lowStockCount: Int,
    @SerialName("out_of_stock_count") val outOfStockCount: Int,
    @SerialName("total_customers") val totalCustomers: Int,
    @SerialName("total_suppliers") val totalSuppliers: Int,
    @SerialName("draft_receipts_count") val draftReceiptsCount: Int,
)
```

- [ ] **Step 2: Thêm vào ReportApi**

Trong `ReportApi.kt`, thêm import `com.mykiot.pos.core.network.dto.HubSummaryDto` (theo đúng thứ tự alphabet với các import DTO khác) và thêm method vào interface (ngay sau `dashboard()`):

```kotlin
    @GET("reports/hub-summary") suspend fun hubSummary(): HubSummaryDto
```

- [ ] **Step 3: Thêm vào ReportRepository**

Trong `ReportRepository.kt`, thêm import `com.mykiot.pos.core.network.dto.HubSummaryDto` và thêm method (ngay sau `dashboard()`):

```kotlin
    open suspend fun hubSummary(): ApiResult<HubSummaryDto> =
        runCatching { reportApi.hubSummary() }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
```

- [ ] **Step 4: Compile**

Run (từ `android/`): `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/dto/ReportDtos.kt android/app/src/main/java/com/mykiot/pos/core/network/ReportApi.kt android/app/src/main/java/com/mykiot/pos/feature/report/data/ReportRepository.kt
git commit -m "feat(android): thêm HubSummaryDto + ReportApi/ReportRepository.hubSummary()

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Android — string resources mới cho Hub

**Files:**
- Modify: `android/app/src/main/res/values/strings_core.xml`

**Interfaces:**
- Produces: các resource id dùng ở Task 4 (`captionFor`) và Task 6 (`HubScreen`): `core_hub_greeting_owner`, `core_hub_greeting_cashier`, `core_hub_group_quick`, `core_hub_group_manage`, `core_hub_group_other`, `core_hub_settings_desc`, `core_hub_caption_inventory_out`, `core_hub_caption_inventory_low`, `core_hub_caption_inventory_ok`, `core_hub_caption_inventory_fallback`, `core_hub_caption_products`, `core_hub_caption_products_fallback`, `core_hub_caption_customers`, `core_hub_caption_customers_fallback`, `core_hub_caption_suppliers`, `core_hub_caption_suppliers_fallback`, `core_hub_caption_receipt_draft`, `core_hub_caption_receipt_fallback`, `core_hub_caption_returns`, `core_hub_caption_categories`, `core_hub_caption_receipt_history`, `core_hub_caption_invoices`, `core_hub_caption_report`.

- [ ] **Step 1: Thêm chuỗi mới**

Trong `strings_core.xml`, thay thế 2 dòng nhóm hub cũ:
```xml
    <!-- Nhóm hub -->
    <string name="core_hub_group_inventory">Kho</string>
    <string name="core_hub_group_catalog">Danh mục</string>
    <string name="core_hub_group_sales">Bán hàng</string>
    <string name="core_hub_group_report">Báo cáo</string>
    <string name="core_hub_group_system">Hệ thống</string>
```
bằng:
```xml
    <!-- Dòng chào theo vai trò -->
    <string name="core_hub_greeting_owner">Xin chào, Chủ cửa hàng</string>
    <string name="core_hub_greeting_cashier">Xin chào, Thu ngân</string>
    <string name="core_hub_settings_desc">Cài đặt</string>

    <!-- Nhóm hub -->
    <string name="core_hub_group_quick">Thao tác nhanh</string>
    <string name="core_hub_group_manage">Quản lý</string>
    <string name="core_hub_group_other">Khác</string>

    <!-- Caption dòng phụ mỗi card -->
    <string name="core_hub_caption_inventory_out">%1$d hết hàng</string>
    <string name="core_hub_caption_inventory_low">%1$d sắp hết hàng</string>
    <string name="core_hub_caption_inventory_ok">Đủ hàng</string>
    <string name="core_hub_caption_inventory_fallback">Xem tồn kho</string>
    <string name="core_hub_caption_products">%1$s sản phẩm · %2$d sắp hết</string>
    <string name="core_hub_caption_products_fallback">Xem danh sách</string>
    <string name="core_hub_caption_customers">%1$d khách hàng</string>
    <string name="core_hub_caption_customers_fallback">Xem danh sách</string>
    <string name="core_hub_caption_suppliers">%1$d nhà cung cấp</string>
    <string name="core_hub_caption_suppliers_fallback">Xem danh sách</string>
    <string name="core_hub_caption_receipt_draft">%1$d phiếu chờ</string>
    <string name="core_hub_caption_receipt_fallback">Tạo phiếu nhập mới</string>
    <string name="core_hub_caption_returns">Xử lý trả hàng</string>
    <string name="core_hub_caption_categories">Quản lý nhóm hàng</string>
    <string name="core_hub_caption_receipt_history">Xem chi tiết</string>
    <string name="core_hub_caption_invoices">Xem lịch sử bán</string>
    <string name="core_hub_caption_report">Xem tổng quan</string>
```

> Giữ nguyên toàn bộ chuỗi khác trong file (`core_hub_receipt`, `core_hub_inventory`, `core_hub_change_password`, v.v. — vẫn dùng làm tên card + mục menu, không xóa).

- [ ] **Step 2: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL (XML resource chỉ báo lỗi khi build; nếu `core_hub_group_inventory`/`core_hub_group_catalog`/`core_hub_group_sales`/`core_hub_group_system` còn được tham chiếu ở đâu đó sẽ FAIL — nếu vậy, đó là do `HubScreen.kt` chưa cập nhật, sẽ sửa ở Task 6; nếu Task này chạy độc lập trước Task 6, tạm thời có thể build lỗi tham chiếu string đã xóa — chấp nhận, sẽ xanh sau Task 6. Ghi rõ trong báo cáo nếu build đỏ vì lý do này.)

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/res/values/strings_core.xml
git commit -m "feat(android): thêm chuỗi cho Hub mới (chào theo vai trò, nhóm, caption card)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Android — `formatCount()` + `captionFor()` (TDD)

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/util/Money.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/navigation/HubCaptions.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/core/util/FormatCountTest.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/navigation/HubCaptionsTest.kt`

**Interfaces:**
- Consumes: `HubSummaryDto` (Task 2), `ResProvider`/`FakeResProvider` (đã có sẵn trong `com.mykiot.pos.core.i18n`), `Routes` (đã có sẵn), string resource id từ Task 3.
- Produces: `fun formatCount(n: Int): String`, `fun captionFor(route: String, summary: HubSummaryDto?, res: ResProvider): String` — Task 5 (`HubViewModel`) dùng trực tiếp.

- [ ] **Step 1: Viết test thất bại cho `formatCount`**

Tạo `android/app/src/test/java/com/mykiot/pos/core/util/FormatCountTest.kt`:

```kotlin
package com.mykiot.pos.core.util

import org.junit.Assert.assertEquals
import org.junit.Test

class FormatCountTest {
    @Test fun `so nho hon 1000 khong co dau cham`() =
        assertEquals("87", formatCount(87))

    @Test fun `so hang nghin co dau cham ngan cach`() =
        assertEquals("1.234", formatCount(1234))

    @Test fun `so 0 tra ve dung 0`() =
        assertEquals("0", formatCount(0))

    @Test fun `so am co dau tru`() =
        assertEquals("-5", formatCount(-5))
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.util.FormatCountTest"`
Expected: FAIL (unresolved reference `formatCount`).

- [ ] **Step 3: Viết `formatCount`**

Thêm vào cuối `android/app/src/main/java/com/mykiot/pos/core/util/Money.kt`:

```kotlin

/** "1.234" — số nguyên có dấu chấm ngăn nghìn kiểu VN, không đơn vị. */
fun formatCount(n: Int): String {
    val digits = kotlin.math.abs(n).toString().reversed().chunked(3).joinToString(".").reversed()
    val sign = if (n < 0) "-" else ""
    return "$sign$digits"
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.util.FormatCountTest"`
Expected: PASS (4/4).

- [ ] **Step 5: Viết test thất bại cho `captionFor`**

Tạo `android/app/src/test/java/com/mykiot/pos/navigation/HubCaptionsTest.kt`:

```kotlin
package com.mykiot.pos.navigation

import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.dto.HubSummaryDto
import org.junit.Assert.assertEquals
import org.junit.Test

class HubCaptionsTest {
    private val res = FakeResProvider()
    private val summary = HubSummaryDto(
        totalProducts = 1234,
        lowStockCount = 12,
        outOfStockCount = 0,
        totalCustomers = 87,
        totalSuppliers = 15,
        draftReceiptsCount = 3,
    )

    @Test fun `ton kho null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_fallback),
            captionFor(Routes.INVENTORY, null, res),
        )

    @Test fun `ton kho het hang uu tien hon sap het`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_out, 2),
            captionFor(Routes.INVENTORY, summary.copy(outOfStockCount = 2, lowStockCount = 5), res),
        )

    @Test fun `ton kho sap het khi out la 0`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_low, 12),
            captionFor(Routes.INVENTORY, summary, res),
        )

    @Test fun `ton kho du hang khi ca hai deu 0`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_ok),
            captionFor(Routes.INVENTORY, summary.copy(lowStockCount = 0, outOfStockCount = 0), res),
        )

    @Test fun `san pham co so lieu dung total va low stock`() =
        assertEquals(
            res.get(R.string.core_hub_caption_products, "1.234", 12),
            captionFor(Routes.PRODUCTS, summary, res),
        )

    @Test fun `san pham null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_products_fallback),
            captionFor(Routes.PRODUCTS, null, res),
        )

    @Test fun `khach hang co so lieu`() =
        assertEquals(
            res.get(R.string.core_hub_caption_customers, 87),
            captionFor(Routes.CUSTOMERS, summary, res),
        )

    @Test fun `khach hang null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_customers_fallback),
            captionFor(Routes.CUSTOMERS, null, res),
        )

    @Test fun `nha cung cap co so lieu`() =
        assertEquals(
            res.get(R.string.core_hub_caption_suppliers, 15),
            captionFor(Routes.SUPPLIERS, summary, res),
        )

    @Test fun `nha cung cap null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_suppliers_fallback),
            captionFor(Routes.SUPPLIERS, null, res),
        )

    @Test fun `nhap hang co so lieu phieu cho`() =
        assertEquals(
            res.get(R.string.core_hub_caption_receipt_draft, 3),
            captionFor(Routes.RECEIPT, summary, res),
        )

    @Test fun `nhap hang null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_receipt_fallback),
            captionFor(Routes.RECEIPT, null, res),
        )

    @Test fun `tra hang luon tinh bat ke summary`() {
        val expected = res.get(R.string.core_hub_caption_returns)
        assertEquals(expected, captionFor(Routes.RETURNS, null, res))
        assertEquals(expected, captionFor(Routes.RETURNS, summary, res))
    }

    @Test fun `nhom hang luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_categories), captionFor(Routes.CATEGORIES, summary, res))

    @Test fun `lich su nhap luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_receipt_history), captionFor(Routes.RECEIPT_HISTORY, summary, res))

    @Test fun `hoa don luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_invoices), captionFor(Routes.INVOICE_HISTORY, summary, res))

    @Test fun `bao cao luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_report), captionFor(Routes.REPORT, summary, res))
}
```

- [ ] **Step 6: Chạy test — kỳ vọng FAIL**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.navigation.HubCaptionsTest"`
Expected: FAIL (unresolved reference `captionFor`).

- [ ] **Step 7: Viết `captionFor`**

Tạo `android/app/src/main/java/com/mykiot/pos/navigation/HubCaptions.kt`:

```kotlin
package com.mykiot.pos.navigation

import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.dto.HubSummaryDto
import com.mykiot.pos.core.util.formatCount

/**
 * Dòng phụ hiển thị dưới tên mỗi card Hub. Số thật nếu [summary] có sẵn cho route đó
 * (out_of_stock ưu tiên hơn low_stock cho Tồn kho); ngược lại dùng caption tĩnh mô tả.
 * Vài route (Trả hàng, Nhóm hàng, Lịch sử nhập, Hóa đơn, Báo cáo) luôn tĩnh — không có
 * số liệu phù hợp (xem spec mục 2.5).
 */
fun captionFor(route: String, summary: HubSummaryDto?, res: ResProvider): String = when (route) {
    Routes.INVENTORY -> when {
        summary == null -> res.get(R.string.core_hub_caption_inventory_fallback)
        summary.outOfStockCount > 0 -> res.get(R.string.core_hub_caption_inventory_out, summary.outOfStockCount)
        summary.lowStockCount > 0 -> res.get(R.string.core_hub_caption_inventory_low, summary.lowStockCount)
        else -> res.get(R.string.core_hub_caption_inventory_ok)
    }
    Routes.PRODUCTS -> if (summary == null) {
        res.get(R.string.core_hub_caption_products_fallback)
    } else {
        res.get(R.string.core_hub_caption_products, formatCount(summary.totalProducts), summary.lowStockCount)
    }
    Routes.CUSTOMERS -> if (summary == null) {
        res.get(R.string.core_hub_caption_customers_fallback)
    } else {
        res.get(R.string.core_hub_caption_customers, summary.totalCustomers)
    }
    Routes.SUPPLIERS -> if (summary == null) {
        res.get(R.string.core_hub_caption_suppliers_fallback)
    } else {
        res.get(R.string.core_hub_caption_suppliers, summary.totalSuppliers)
    }
    Routes.RECEIPT -> if (summary == null) {
        res.get(R.string.core_hub_caption_receipt_fallback)
    } else {
        res.get(R.string.core_hub_caption_receipt_draft, summary.draftReceiptsCount)
    }
    Routes.RETURNS -> res.get(R.string.core_hub_caption_returns)
    Routes.CATEGORIES -> res.get(R.string.core_hub_caption_categories)
    Routes.RECEIPT_HISTORY -> res.get(R.string.core_hub_caption_receipt_history)
    Routes.INVOICE_HISTORY -> res.get(R.string.core_hub_caption_invoices)
    Routes.REPORT -> res.get(R.string.core_hub_caption_report)
    else -> ""
}
```

- [ ] **Step 8: Chạy test — kỳ vọng PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.navigation.HubCaptionsTest"`
Expected: PASS (18/18).

- [ ] **Step 9: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/util/Money.kt android/app/src/main/java/com/mykiot/pos/navigation/HubCaptions.kt android/app/src/test/java/com/mykiot/pos/core/util/FormatCountTest.kt android/app/src/test/java/com/mykiot/pos/navigation/HubCaptionsTest.kt
git commit -m "feat(android): formatCount + captionFor cho dòng phụ card Hub (có test)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Android — `HubViewModel` gọi API + tính caption

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HubViewModel.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/navigation/HubViewModelTest.kt`

**Interfaces:**
- Consumes: `ReportRepository.hubSummary()` (Task 2), `captionFor()` (Task 4), `ResProvider` (có sẵn).
- Produces: `data class HubUiState(val captions: Map<String, String> = emptyMap())`, `HubViewModel.state: StateFlow<HubUiState>`, `HubViewModel.load()` — Task 6 (`HubScreen`) đọc `state.captions[route]` và gọi `load()` trong `LaunchedEffect(Unit)`.

- [ ] **Step 1: Viết test thất bại**

Tạo `android/app/src/test/java/com/mykiot/pos/navigation/HubViewModelTest.kt`:

```kotlin
package com.mykiot.pos.navigation

import com.mykiot.pos.R
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.HubSummaryDto
import com.mykiot.pos.feature.report.data.ReportRepository
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class HubViewModelTest {
    private val sessionManager = mockk<SessionManager>(relaxed = true)
    private val reportRepository = mockk<ReportRepository>()
    private val res = FakeResProvider()

    @Before fun setUp() {
        Dispatchers.setMain(StandardTestDispatcher())
        every { sessionManager.current } returns MutableStateFlow(null)
    }

    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `truoc khi load dung caption fallback`() = runTest {
        val vm = HubViewModel(sessionManager, reportRepository, res)
        assertEquals(
            res.get(R.string.core_hub_caption_products_fallback),
            vm.state.value.captions[Routes.PRODUCTS],
        )
    }

    @Test
    fun `load thanh cong dien so lieu that`() = runTest {
        val summary = HubSummaryDto(
            totalProducts = 1234, lowStockCount = 12, outOfStockCount = 0,
            totalCustomers = 87, totalSuppliers = 15, draftReceiptsCount = 3,
        )
        coEvery { reportRepository.hubSummary() } returns ApiResult.Success(summary)
        val vm = HubViewModel(sessionManager, reportRepository, res)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(
            res.get(R.string.core_hub_caption_products, "1.234", 12),
            vm.state.value.captions[Routes.PRODUCTS],
        )
        assertEquals(
            res.get(R.string.core_hub_caption_receipt_draft, 3),
            vm.state.value.captions[Routes.RECEIPT],
        )
    }

    @Test
    fun `load that bai giu caption fallback`() = runTest {
        coEvery { reportRepository.hubSummary() } returns ApiResult.Failure(ApiError("NETWORK_ERROR", "Lỗi mạng"))
        val vm = HubViewModel(sessionManager, reportRepository, res)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(
            res.get(R.string.core_hub_caption_products_fallback),
            vm.state.value.captions[Routes.PRODUCTS],
        )
    }
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.navigation.HubViewModelTest"`
Expected: FAIL (constructor `HubViewModel` chưa nhận `ReportRepository`/`ResProvider`, chưa có `state`/`load()`).

- [ ] **Step 3: Sửa `HubViewModel.kt`**

Thay toàn bộ nội dung `android/app/src/main/java/com/mykiot/pos/navigation/HubViewModel.kt` bằng:

```kotlin
package com.mykiot.pos.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.HubSummaryDto
import com.mykiot.pos.feature.report.data.ReportRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HubUiState(
    val captions: Map<String, String> = emptyMap(),
)

private val HUB_CAPTION_ROUTES = listOf(
    Routes.INVENTORY, Routes.PRODUCTS, Routes.CUSTOMERS, Routes.SUPPLIERS, Routes.RECEIPT,
    Routes.RETURNS, Routes.CATEGORIES, Routes.RECEIPT_HISTORY, Routes.INVOICE_HISTORY, Routes.REPORT,
)

@HiltViewModel
class HubViewModel @Inject constructor(
    sessionManager: SessionManager,
    private val reportRepository: ReportRepository,
    private val res: ResProvider,
) : ViewModel() {
    val user: StateFlow<CurrentUser?> = sessionManager.current

    private val _state = MutableStateFlow(HubUiState(captions = buildCaptions(null)))
    val state: StateFlow<HubUiState> = _state.asStateFlow()

    /** Tải số liệu tổng hợp cho Hub; lỗi thì giữ nguyên caption tĩnh (không báo lỗi). */
    fun load() {
        viewModelScope.launch {
            val summary = when (val r = reportRepository.hubSummary()) {
                is ApiResult.Success -> r.data
                is ApiResult.Failure -> null
            }
            _state.update { it.copy(captions = buildCaptions(summary)) }
        }
    }

    private fun buildCaptions(summary: HubSummaryDto?): Map<String, String> =
        HUB_CAPTION_ROUTES.associateWith { route -> captionFor(route, summary, res) }
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.navigation.HubViewModelTest"`
Expected: PASS (3/3).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HubViewModel.kt android/app/src/test/java/com/mykiot/pos/navigation/HubViewModelTest.kt
git commit -m "feat(android): HubViewModel gọi hub-summary, tính caption theo route (có test)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Android — `HubScreen.kt` (nhóm mới, card thu nhỏ, header Cài đặt)

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt`

**Interfaces:**
- Consumes: `HubViewModel.state` (Task 5, field `captions: Map<String, String>`), `HubViewModel.load()`, string resource từ Task 3, `Routes` (có sẵn).

- [ ] **Step 1: Thay toàn bộ nội dung file**

Thay toàn bộ `android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt` bằng:

```kotlin
package com.mykiot.pos.navigation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.AssignmentReturn
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.Assessment
import androidx.compose.material.icons.outlined.Category
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.LocalShipping
import androidx.compose.material.icons.outlined.PointOfSale
import androidx.compose.material.icons.outlined.Sell
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.annotation.StringRes
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.AppHeader

private data class HubItem(
    @StringRes val label: Int,
    val route: String,
    val icon: ImageVector,
    val ownerOnly: Boolean = false,
)

private data class HubGroup(@StringRes val title: Int, val items: List<HubItem>)

private val hubGroups = listOf(
    HubGroup(
        R.string.core_hub_group_quick,
        listOf(
            HubItem(R.string.core_hub_inventory, Routes.INVENTORY, Icons.Outlined.Inventory2),
            HubItem(R.string.core_hub_receipt, Routes.RECEIPT, Icons.AutoMirrored.Outlined.ReceiptLong),
            HubItem(R.string.core_hub_products, Routes.PRODUCTS, Icons.Outlined.Sell),
            HubItem(R.string.core_hub_customers, Routes.CUSTOMERS, Icons.Outlined.Group),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_manage,
        listOf(
            HubItem(R.string.core_hub_suppliers, Routes.SUPPLIERS, Icons.Outlined.LocalShipping),
            HubItem(R.string.core_hub_categories, Routes.CATEGORIES, Icons.Outlined.Category),
            HubItem(R.string.core_hub_receipt_history, Routes.RECEIPT_HISTORY, Icons.Outlined.History),
            HubItem(R.string.core_hub_returns, Routes.RETURNS, Icons.AutoMirrored.Outlined.AssignmentReturn),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_other,
        listOf(
            HubItem(R.string.core_hub_invoices, Routes.INVOICE_HISTORY, Icons.Outlined.Description),
            HubItem(R.string.core_hub_report, Routes.REPORT, Icons.Outlined.Assessment, ownerOnly = true),
        ),
    ),
)

@Composable
fun HubScreen(
    onNavigate: (String) -> Unit,
    onOpenPos: () -> Unit,
    onLogout: () -> Unit,
    viewModel: HubViewModel = hiltViewModel(),
) {
    val user by viewModel.user.collectAsStateWithLifecycle()
    val state by viewModel.state.collectAsStateWithLifecycle()
    val isOwner = user?.role == "OWNER"
    val visibleGroups = hubGroups
        .map { g -> g.copy(items = g.items.filter { !it.ownerOnly || isOwner }) }
        .filter { it.items.isNotEmpty() }

    LaunchedEffect(Unit) { viewModel.load() }

    var showLogoutConfirm by remember { mutableStateOf(false) }
    var showSettingsMenu by remember { mutableStateOf(false) }

    if (showLogoutConfirm) {
        AlertDialog(
            onDismissRequest = { showLogoutConfirm = false },
            title = { Text(stringResource(R.string.common_logout)) },
            text = { Text(stringResource(R.string.core_logout_confirm_message)) },
            confirmButton = {
                TextButton(
                    onClick = { showLogoutConfirm = false; onLogout() },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.error,
                    ),
                ) { Text(stringResource(R.string.common_logout)) }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutConfirm = false }) { Text(stringResource(R.string.common_cancel)) }
            },
        )
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = stringResource(
                    if (isOwner) R.string.core_hub_greeting_owner else R.string.core_hub_greeting_cashier,
                ),
                modifier = Modifier.padding(horizontal = 16.dp),
                actions = {
                    Box {
                        IconButton(onClick = { showSettingsMenu = true }) {
                            Icon(
                                Icons.Outlined.Settings,
                                contentDescription = stringResource(R.string.core_hub_settings_desc),
                            )
                        }
                        DropdownMenu(
                            expanded = showSettingsMenu,
                            onDismissRequest = { showSettingsMenu = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text(stringResource(R.string.core_hub_change_password)) },
                                onClick = {
                                    showSettingsMenu = false
                                    onNavigate(Routes.CHANGE_PASSWORD)
                                },
                            )
                            DropdownMenuItem(
                                text = { Text(stringResource(R.string.common_logout)) },
                                onClick = {
                                    showSettingsMenu = false
                                    showLogoutConfirm = true
                                },
                            )
                        }
                    }
                },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
        ) {
            PosButton(onClick = onOpenPos)
            Spacer(Modifier.height(20.dp))
            visibleGroups.forEachIndexed { index, group ->
                Text(
                    stringResource(group.title).uppercase(),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Spacer(Modifier.height(10.dp))
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 2000.dp),
                    userScrollEnabled = false,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(group.items, key = { it.route }) { item ->
                        HubCard(
                            item = item,
                            caption = state.captions[item.route] ?: "",
                            onClick = { onNavigate(item.route) },
                        )
                    }
                }
                if (index != visibleGroups.lastIndex) Spacer(Modifier.height(20.dp))
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun PosButton(onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.primary,
        contentColor = MaterialTheme.colorScheme.onPrimary,
        shadowElevation = 2.dp,
        modifier = Modifier
            .fillMaxWidth()
            .height(76.dp),
    ) {
        Row(
            Modifier
                .fillMaxSize()
                .padding(horizontal = 22.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.PointOfSale, contentDescription = null)
            Spacer(Modifier.width(14.dp))
            Column {
                Text(stringResource(R.string.core_pos_button_title), style = MaterialTheme.typography.titleLarge)
                Text(
                    stringResource(R.string.core_pos_button_subtitle),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f),
                )
            }
        }
    }
}

@Composable
private fun HubCard(item: HubItem, caption: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        shadowElevation = 1.dp,
        modifier = Modifier
            .fillMaxWidth()
            .height(84.dp),
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .padding(12.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Icon(
                    item.icon,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.size(22.dp),
                )
                Icon(
                    Icons.Outlined.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.outline,
                    modifier = Modifier.size(16.dp),
                )
            }
            Column {
                Text(
                    stringResource(item.label),
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                )
                Text(
                    caption,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                )
            }
        }
    }
}
```

- [ ] **Step 2: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Chạy toàn bộ unit test liên quan**

Run: `./gradlew :app:testDebugUnitTest`
Expected: PASS toàn bộ (bao gồm `HubCaptionsTest`, `HubViewModelTest`, `FormatCountTest` từ các task trước).

- [ ] **Step 4: Rà soát trực quan**

Chạy app (hoặc preview), mở Hub: dòng chào theo vai trò, icon Cài đặt ở góc phải mở đúng menu (Đổi mật khẩu, Đăng xuất — đăng xuất vẫn hiện dialog xác nhận), 3 nhóm đúng thứ tự card, card nhỏ hơn có dòng số liệu (hoặc caption tĩnh nếu offline/lỗi), Báo cáo vẫn ẩn với tài khoản CASHIER.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt
git commit -m "feat(hub): sắp xếp lại nhóm/card, thu nhỏ card có caption, menu Cài đặt thay nút Đăng xuất

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (đã thực hiện khi viết plan)

- **Spec coverage:** mục 2.1 (header/dropdown) → Task 6; 2.2 (nhóm/thứ tự) → Task 6; 2.3 (kích thước card) → Task 6; 2.4 (nội dung caption) → Task 3+4; 2.5 (Trả hàng tĩnh) → Task 4; 2.6 (lỗi → fallback) → Task 4+5; mục 3 (API backend) → Task 1; mục 4 (DTO/ViewModel/captionFor) → Task 2+4+5.
- **Placeholder scan:** không có TBD/TODO; mọi step có code/lệnh cụ thể. Đã xác nhận `ApiError(code: String, message: String, httpStatus: Int? = null)` khớp đúng cách dùng trong test Task 5.
- **Type consistency:** `HubSummaryDto` (6 field) dùng nhất quán ở Task 2 (định nghĩa), Task 4 (`captionFor` tham số + test), Task 5 (`buildCaptions`/test). `captionFor(route: String, summary: HubSummaryDto?, res: ResProvider): String` dùng đúng chữ ký ở Task 4 và Task 5. `HubUiState(captions: Map<String, String>)` dùng nhất quán Task 5–6. Route constants (`Routes.INVENTORY`, `Routes.PRODUCTS`...) đã có sẵn trong `Routes.kt`, không cần thêm.
