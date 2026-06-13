# Android App — Hoàn thiện tính năng còn lại

**Ngày:** 2026-06-13  
**Branch:** fix/return-debt-business-logic  
**Scope:** Search bar chuẩn hóa + fix network + màn Sản phẩm + Hóa đơn + Trả hàng

---

## 1. Bối cảnh & Vấn đề

Ứng dụng Android đã hoạt động cho 5 màn: POS, Nhập hàng, Tồn kho, Khách hàng, Báo cáo.  
3 chức năng này (và POS, Nhập kho) đều báo lỗi mạng khi test trên thiết bị thật vì `BASE_URL_DEBUG` trỏ tới `10.0.2.2` (địa chỉ emulator, không dùng được trên thiết bị vật lý).

Còn 3 màn placeholder chưa build: **Sản phẩm**, **Hóa đơn**, **Trả hàng**.

Thêm vào đó, `AppSearchField` render chiều cao khác nhau tùy màn do Material3 `OutlinedTextField` không nhất quán khi có/không có trailing icon.

---

## 2. Fix network — Thiết bị thật + localhost

### Nguyên nhân
`BASE_URL_DEBUG = "http://10.0.2.2:8000/api/v1/"` — địa chỉ này do Android Emulator dùng để trỏ về localhost của máy host. Thiết bị thật không hiểu địa chỉ này.

### Giải pháp
Thêm vào `local.properties` (không commit, gitignored):
```
BASE_URL_DEBUG=http://<IP_MÁY_TÍNH>:8000/api/v1/
```

IP máy tính lấy bằng `ipconfig` (Windows) hoặc `ifconfig` (Mac/Linux) — cùng mạng wifi với điện thoại.

**Không thay đổi code** — `build.gradle.kts` đã đọc từ `local.properties` với fallback về `10.0.2.2`.

---

## 3. Search bar chuẩn hóa — 56dp

### Hiện trạng
`AppSearchField` dùng `OutlinedTextField` không set chiều cao cứng. Material3 render khác nhau tùy context.

### Giải pháp
Thêm `Modifier.height(56.dp)` vào `modifier` param mặc định trong `AppSearchField` tại `Components.kt`:

```kotlin
@Composable
fun AppSearchField(
    ...
    modifier: Modifier = Modifier,
    ...
) {
    OutlinedTextField(
        ...
        modifier = modifier.height(56.dp),  // ← thêm dòng này
    )
}
```

Tất cả 4 màn dùng `AppSearchField` sẽ đồng nhất 56dp mà không cần sửa từng màn.

---

## 4. Màn Sản phẩm (ProductListScreen)

### API mới — ProductApi.kt
```kotlin
@GET("products")
suspend fun list(
    @Query("search") search: String? = null,
    @Query("page") page: Int = 1,
    @Query("limit") limit: Int = 30,
    @Query("status") status: String? = null,
): ProductListDto
```

### DTO mới — ProductDtos.kt
```kotlin
@Serializable
data class ProductListDto(
    val items: List<ProductBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)
```
*(PaginationDto đã có trong InventoryDtos.kt — move sang `core/network/dto/CommonDtos.kt` mới để tránh duplicate, cập nhật import ở InventoryDtos.kt)*

### Architecture
```
ProductListScreen → ProductListViewModel → ProductListRepository → ProductApi
```

### ProductListUiState
```kotlin
data class ProductListUiState(
    val loading: Boolean = false,
    val items: List<ProductBriefDto> = emptyList(),
    val query: String = "",
    val errorMessage: String? = null,
)
```

### ProductListViewModel
- `init { load() }` — tải ngay khi mở
- `onQueryChange(q)` — debounce 300ms rồi gọi `load()`
- `load()` — gọi `repository.list(query)`

### ProductListScreen — UI
- Cấu trúc giống `CustomerListScreen`
- `AppHeader("Sản phẩm", onBack)` + FAB "+" mở `AddProductScreen`
- `AppSearchField` — tìm theo tên / SKU
- `LazyColumn` — mỗi card:
  - Dòng 1: tên SP (SemiBold) + badge trạng thái (INACTIVE = `MonoBadge` xám)
  - Dòng 2: SKU • đơn vị • giá bán (formatVnd)
- Empty state: "Chưa có sản phẩm"

### Navigation (HomeNavHost.kt)
```kotlin
composable(Routes.PRODUCTS) {
    ProductListScreen(
        onBack = { nav.popBackStack() },
        onAdd = { /* nav đến AddProduct — Phase sau */ },
    )
}
```

---

## 5. Màn Hóa đơn (InvoiceListScreen)

### API mới — SalesApi.kt
```kotlin
@GET("invoices")
suspend fun list(
    @Query("status") status: String? = null,
    @Query("page") page: Int = 1,
    @Query("limit") limit: Int = 20,
): InvoiceListDto

@POST("invoices/{id}/cancel")
suspend fun cancel(
    @Path("id") id: Long,
    @Body body: CancelInvoiceDto,
): InvoiceDto
```

### DTO mới
```kotlin
@Serializable
data class InvoiceListItemDto(
    val id: Long,
    val code: String,
    val total: String,
    val status: String,
    @SerialName("customer_name") val customerName: String? = null,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class InvoiceListDto(
    val items: List<InvoiceListItemDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

@Serializable
data class CancelInvoiceDto(val reason: String)
```

### Architecture
```
InvoiceListScreen → InvoiceListViewModel → InvoiceListRepository → SalesApi
```

### InvoiceListUiState
```kotlin
data class InvoiceListUiState(
    val loading: Boolean = false,
    val items: List<InvoiceListItemDto> = emptyList(),
    val cancelingId: Long? = null,   // hiển thị confirm dialog
    val errorMessage: String? = null,
    val userRole: String = "CASHIER",
)
```

### InvoiceListScreen — UI
- Header "Hóa đơn" + back
- Filter nhanh (Row): chip "Tất cả" / "Đã bán" / "Đã hủy" — lọc trên client (items đã load)
- `LazyColumn` — mỗi card:
  - Dòng 1: mã HĐ (SemiBold) + thời gian
  - Dòng 2: tên KH (hoặc "Khách lẻ") + tổng tiền
  - Badge: COMPLETED (xanh slate) / CANCELLED (đỏ nhạt)
- OWNER: nhấn vào card → bottom sheet / dialog với nút "Hủy hóa đơn"
- Confirm dialog hủy: textarea lý do (bắt buộc)

### Navigation
```kotlin
composable(Routes.INVOICE_HISTORY) {
    InvoiceListScreen(onBack = { nav.popBackStack() })
}
```

---

## 6. Màn Trả hàng (ReturnsScreen) — Hướng A

### Quyết định thiết kế
"Trả hàng" = hủy toàn bộ hóa đơn đã hoàn tất (gọi `/invoices/{id}/cancel`, OWNER only).  
Backend đã xử lý: cộng lại tồn kho, đảo bút toán KH, tạo `CANCEL_SALE` stock movement.

### Cách triển khai
Tạo `ReturnsViewModel` kế thừa `InvoiceListViewModel`, override `initialStatus = "COMPLETED"` để luôn lọc hóa đơn đã hoàn tất ngay khi `init`.  
Tái dùng `InvoiceListRepository`.  
Tạo `ReturnsScreen` riêng (không phải alias của InvoiceListScreen) để:
- Tiêu đề là "Trả hàng" 
- Chỉ hiện hóa đơn COMPLETED (không có filter chip)
- Nút action label "Trả hàng" thay vì "Hủy hóa đơn"
- Confirm dialog: "Xác nhận trả hàng? Tồn kho sẽ được cộng lại."

### Navigation
```kotlin
composable(Routes.RETURNS) {
    ReturnsScreen(onBack = { nav.popBackStack() })
}
```

---

## 7. Phạm vi thay đổi file

| File | Thay đổi |
|------|----------|
| `local.properties` | Thêm `BASE_URL_DEBUG` với IP thật (hướng dẫn user) |
| `core/ui/Components.kt` | `AppSearchField`: thêm `.height(56.dp)` |
| `core/network/ProductApi.kt` | Thêm `list()` |
| `core/network/SalesApi.kt` | Thêm `list()` và `cancel()` |
| `core/network/dto/ProductDtos.kt` | Thêm `ProductListDto` |
| `core/network/dto/ProductDtos.kt` | Move `PaginationDto` vào đây hoặc tạo `CommonDtos.kt` |
| `core/network/dto/InvoiceDtos.kt` (mới) | `InvoiceListItemDto`, `InvoiceListDto`, `CancelInvoiceDto` |
| `feature/product/ProductListScreen.kt` (mới) | UI màn Sản phẩm |
| `feature/product/ProductListViewModel.kt` (mới) | ViewModel |
| `feature/product/ProductListUiState.kt` (mới) | State |
| `feature/product/data/ProductListRepository.kt` (mới) | Repository |
| `feature/invoice/InvoiceListScreen.kt` (mới) | UI màn Hóa đơn |
| `feature/invoice/InvoiceListViewModel.kt` (mới) | ViewModel |
| `feature/invoice/InvoiceListUiState.kt` (mới) | State |
| `feature/invoice/data/InvoiceListRepository.kt` (mới) | Repository |
| `feature/invoice/ReturnsViewModel.kt` (mới) | Kế thừa InvoiceListViewModel, filter COMPLETED |
| `feature/invoice/ReturnsScreen.kt` (mới) | UI màn Trả hàng (dùng ReturnsViewModel) |
| `navigation/HomeNavHost.kt` | Wire up 3 màn mới, xóa 3 PlaceholderScreen |

---

## 8. Quy ước tuân theo (từ CLAUDE.md)

- Mọi thông báo lỗi UI phải bằng **tiếng Việt**
- `tenant_id` lấy từ JWT, không từ query param
- Tiền dùng `DECIMAL` / `String`, không `Float`
- Format tiền dùng `formatVnd()` đã có
- Dùng lại `AppSearchField`, `AppHeader`, `MonoBadge`, `LoadingDialog`, `ScreenPadding`

---

## 9. Không trong scope

- Xem chi tiết sản phẩm từ ProductListScreen (Phase sau)
- Partial return / CreditNote (Hướng C — Phase 2)
- Phân trang tự động (infinite scroll) — MVP load trang 1 đủ 30 item
- Filter theo ngày trên InvoiceListScreen (MVP lọc trên client)
