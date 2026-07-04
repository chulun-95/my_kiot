# Thiết kế: Badge cảnh báo tồn kho trong danh sách Sản phẩm

**Ngày:** 2026-07-04
**Trạng thái:** Đã duyệt hướng thiết kế, chờ review spec
**Phạm vi:** Backend (`backend/modules/product/`) + App Android (`feature/product/ProductListScreen.kt`, `core/network/dto/ProductDtos.kt`)

---

## 1. Bối cảnh & mục tiêu

Màn danh sách Sản phẩm (`ProductListScreen`) hiện chỉ hiện tên, SKU/đơn vị/giá, và badge "Ngừng bán" nếu SP inactive — **không có cảnh báo tồn kho** dù màn Tồn kho (`InventoryScreen`) đã có badge tương tự. Người dùng (chủ shop) muốn thấy ngay SP nào sắp/hết hàng khi lướt danh sách Sản phẩm, không phải chuyển sang màn Tồn kho.

**Phát hiện quan trọng khi khảo sát:** endpoint `GET /api/v1/products` hiện đã trả `min_stock` (qua `ProductResponse`) nhưng **không trả số lượng tồn hiện tại** (nằm ở bảng `inventory` riêng, không join). Vì vậy backend cần bổ sung.

**Mục tiêu:**
1. Backend: `GET /products` (danh sách) trả thêm 1 field phân loại tồn kho cho từng sản phẩm trong trang kết quả.
2. Android: hiện badge "Hết" (đỏ đậm/filled) hoặc "Sắp hết" (nhạt/outline) cạnh tên SP trong danh sách, tái dùng đúng string đã có ở màn Tồn kho.

---

## 2. Quyết định đã chốt (qua brainstorm)

1. **Kiểu hiển thị:** badge trên từng dòng sản phẩm (không phải banner tổng ở đầu danh sách).
2. **Phân loại:** 2 trạng thái riêng biệt — "Hết hàng" (tồn ≤ 0) và "Sắp hết" (0 < tồn ≤ `min_stock`) — giống hệt quy ước đang dùng ở `InventoryScreen` (`inv_badge_out` = "Hết", `inv_badge_low` = "Sắp hết").
3. Sản phẩm có `min_stock = 0` **không bao giờ** bị đánh dấu (đúng quy tắc nghiệp vụ đã áp dụng nhất quán ở Báo cáo/Tồn kho).
4. Chỉ áp dụng cho **danh sách sản phẩm**; không đổi màn chi tiết SP, tạo mới, hay sửa SP.

---

## 3. Backend

### 3.1. Field mới trên `ProductResponse`

Thêm vào `backend/modules/product/schemas.py`, class `ProductResponse`:

```python
stock_status: Literal["OUT", "LOW"] | None = None
```

Mặc định `None` — **không ảnh hưởng** các endpoint khác dùng chung `ProductResponse` (tạo/sửa/xem chi tiết 1 SP) vì chúng không tính giá trị này, giữ nguyên `None`.

### 3.2. Tính toán trong `list_products()`

Trong `backend/modules/product/service.py`, sau khi `paginate()` trả về trang kết quả:
1. Lấy danh sách `product_id` của trang hiện tại.
2. 1 query `SELECT product_id, quantity FROM inventory WHERE tenant_id=? AND product_id IN (...)` (nhẹ — chỉ bằng số SP/trang, tối đa `limit`, không N+1).
3. Với mỗi SP, phân loại bằng hàm thuần:
   - `min_stock <= 0` → `None` (không cảnh báo)
   - tồn `None` (chưa từng nhập) hoặc `<= 0` → `"OUT"`
   - tồn `<= min_stock` → `"LOW"`
   - còn lại → `None`

Kết quả đính kèm vào dict trả về của `list_products()` dưới dạng `stock_by_id: dict[int, str | None]`.

### 3.3. Router

Trong `backend/modules/product/router.py`:
- `_to_product_response(p, user, stock_status=None)` — thêm tham số tùy chọn, đưa vào dict trả về.
- Endpoint `GET /products` (danh sách): gọi `_to_product_response(p, user, stock_status=result["stock_by_id"].get(p.id))` cho từng SP.
- Các call site khác (`detail`, `create`, `update`) **giữ nguyên**, không truyền `stock_status` (mặc định `None`).

### 3.4. Test

Thêm vào `tests/test_product.py` (cạnh nhóm test `test_list_products_*` đã có):
- SP có `min_stock=5`, tồn 3 → `stock_status == "LOW"`.
- SP có `min_stock=5`, tồn 0 (hoặc chưa nhập) → `stock_status == "OUT"`.
- SP có `min_stock=0` bất kể tồn bao nhiêu → `stock_status == None`.
- SP tồn dư dả (> min_stock) → `stock_status == None`.

---

## 4. Android

### 4.1. DTO

`core/network/dto/ProductDtos.kt`, thêm vào `ProductBriefDto`:

```kotlin
@SerialName("stock_status") val stockStatus: String? = null
```

### 4.2. UI — `ProductListScreen.kt`

Trong `ProductListCard`, ngay sau badge "Ngừng bán" hiện có (cùng `Row` với tên SP), thêm:

```kotlin
when (product.stockStatus) {
    "OUT" -> { Spacer(Modifier.width(6.dp)); MonoBadge(stringResource(R.string.inv_badge_out), filled = true) }
    "LOW" -> { Spacer(Modifier.width(6.dp)); MonoBadge(stringResource(R.string.inv_badge_low), filled = false) }
    else -> {}
}
```

Tái dùng nguyên `R.string.inv_badge_out`/`inv_badge_low` (đã có trong `strings_inventory.xml`, dùng cho `InventoryScreen`) — không tạo string trùng nghĩa. Nếu SP vừa "Ngừng bán" vừa sắp/hết hàng, cả 2 badge cùng hiện (không loại trừ nhau).

Không cần hàm thuần/unit test riêng cho logic hiển thị này — đây là ánh xạ 1-1 đơn giản (`stockStatus` string → badge), viết thẳng trong Composable, nhất quán với cách `InventoryScreen` gốc đang xử lý (`out`/`low` boolean → `MonoBadge`).

---

## 5. Ngoài phạm vi (KHÔNG làm)

- Không đổi màn chi tiết sản phẩm, tạo mới, sửa sản phẩm.
- Không đổi màn Tồn kho (đã có badge riêng, không phụ thuộc thay đổi này).
- Không thêm banner tổng số SP sắp/hết hàng ở đầu danh sách.
- Không đổi màu sắc/theme (badge dùng `MonoBadge` đơn sắc sẵn có).
- Không đổi logic phân trang/tìm kiếm/quét mã của màn Sản phẩm.

---

## 6. Rủi ro & lưu ý

- **Hiệu năng:** query tồn kho bổ sung chỉ chạy 1 lần/trang (không phải N+1), giới hạn bởi `limit` (tối đa 100) — không đáng kể.
- **Nhất quán quy tắc:** logic phân loại (`min_stock=0` → bỏ qua; ưu tiên OUT trước LOW) phải khớp chính xác với quy tắc đã dùng ở `report_service._low_stock_counts` (đang được thêm ở plan Hub redesign) — cùng ý nghĩa nghiệp vụ, nhưng đây là 2 đoạn code riêng (khác module, khác hình dạng query per-row vs aggregate) nên **không dùng chung hàm** — chỉ cần đảm bảo cùng công thức.
- **Không phá schema hiện có:** `stock_status` là field mới, optional, mặc định `None` — client Android cũ (nếu có) vẫn parse được nhờ `ignoreUnknownKeys`/default value.

---

## 7. Tiêu chí hoàn thành

- [ ] Backend: `GET /products` trả đúng `stock_status` cho từng SP theo 4 trường hợp ở mục 3.4, có test.
- [ ] Các endpoint khác (`detail`/`create`/`update`) không bị ảnh hưởng (vẫn trả `stock_status: null` hoặc không cần quan tâm).
- [ ] Android: `ProductBriefDto` parse đúng field mới.
- [ ] Danh sách Sản phẩm hiện đúng badge "Hết"/"Sắp hết" cạnh tên SP, đúng màu/kiểu như màn Tồn kho.
- [ ] Build & test pass (`./gradlew :app:testDebugUnitTest`, `./gradlew :app:assembleDebug`; backend `pytest tests/test_product.py`).
