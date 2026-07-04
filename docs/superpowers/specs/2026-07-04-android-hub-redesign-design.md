# Thiết kế: Sắp xếp lại màn Hub (trang chủ) Android + card có số liệu thật

**Ngày:** 2026-07-04
**Trạng thái:** Đã duyệt hướng thiết kế, chờ review spec
**Phạm vi:** Backend (1 endpoint mới) + App Android (`navigation/HubScreen.kt`, `HubViewModel.kt`)

---

## 1. Bối cảnh & mục tiêu

Màn Hub (trang chủ) hiện là lưới 2 cột, 5 nhóm cố định (Kho/Danh mục/Bán hàng/Báo cáo/Hệ thống), mỗi card chỉ có icon + tên + mũi tên, không có thông tin gì thêm. Mục tiêu:

1. **Sắp xếp lại nhóm** theo tần suất/vai trò sử dụng thay vì theo loại dữ liệu kỹ thuật.
2. **Thêm dòng chào cá nhân hóa** theo vai trò (OWNER/CASHIER).
3. **Thu nhỏ card** (đang hơi to so với lượng thông tin hiển thị).
4. **Thêm dòng số liệu thật** vào mỗi card khi có dữ liệu phù hợp (vd "1.234 sản phẩm"), card nào không có dữ liệu phù hợp thì dùng caption mô tả tĩnh.

**Lưu ý:** đây là thiết kế **độc lập, thay thế** cho spec màu teal trước đó (`2026-07-04-android-ui-redesign-design.md`) — spec đó đã bị hủy/revert theo yêu cầu người dùng, giao diện vẫn giữ đơn sắc (đen/trắng/xám) như nguyên bản. Thiết kế này **không đổi màu sắc/theme**, chỉ đổi cấu trúc nội dung và bố cục màn Hub.

---

## 2. Thiết kế UI

### 2.1. Header

Thay tiêu đề tĩnh "my_kiot POS" bằng dòng chào theo vai trò:
- OWNER → "Xin chào, Chủ cửa hàng"
- CASHIER → "Xin chào, Thu ngân"

**Nút "Đăng xuất" (TextButton) được thay bằng icon "Cài đặt" (⚙️, `Icons.Outlined.Settings`).** Bấm vào icon mở `DropdownMenu` với 2 mục:
- "Đổi mật khẩu" → điều hướng `Routes.CHANGE_PASSWORD` (giữ nguyên màn đích, chỉ đổi lối vào).
- "Đăng xuất" → giữ nguyên hành vi hiện tại (mở `AlertDialog` xác nhận `showLogoutConfirm`, không đổi logic).

Nút BÁN HÀNG (POS) giữ nguyên 100% (icon, text, style, hành vi).

### 2.2. Nhóm & thứ tự card (thay 5 nhóm cũ bằng 3 nhóm)

| Nhóm | Card (đúng thứ tự) |
|---|---|
| **THAO TÁC NHANH** | Tồn kho, Nhập hàng, Sản phẩm, Khách hàng |
| **QUẢN LÝ** | Nhà cung cấp, Nhóm hàng, Lịch sử nhập, Trả hàng |
| **KHÁC** | Hóa đơn, Báo cáo (chỉ OWNER — giữ role-gating hiện tại) |

**"Đổi mật khẩu" không còn là card riêng** — chỉ truy cập qua menu Cài đặt ở header (mục 2.1), tránh 2 đường dẫn trùng nhau tới cùng 1 màn.

Route đích của từng card giữ nguyên như hiện tại (không đổi navigation).

### 2.3. Kích thước card (thu nhỏ so với hiện tại)

| Thuộc tính | Hiện tại | Mới |
|---|---|---|
| Chiều cao card | 108dp | **84dp** |
| Icon chính | 30dp | **22dp** |
| Padding trong | 14dp | **12dp** |
| Icon mũi tên (chevron) | mặc định (24dp) | **16dp** |
| Style tên card | `titleMedium` | **`bodyMedium`** |

Cấu trúc mỗi card (không đổi): hàng trên = icon + chevron; giữa = tên; **dưới = dòng phụ mới** (`labelMedium`, màu `onSurfaceVariant`, 1 dòng, luôn có mặt ở mọi card để chiều cao đồng nhất).

### 2.4. Nội dung dòng phụ từng card

| Card | Dòng phụ | Nguồn |
|---|---|---|
| Tồn kho | "X hết hàng" (nếu out>0) / "X sắp hết hàng" (nếu low>0, out=0) / "Đủ hàng" (cả hai =0) | `hub-summary.out_of_stock_count`, `low_stock_count` |
| Sản phẩm | "{total_products} sản phẩm · {low_stock_count} sắp hết" | `hub-summary.total_products`, `low_stock_count` |
| Khách hàng | "{total_customers} khách hàng" | `hub-summary.total_customers` |
| Nhà cung cấp | "{total_suppliers} nhà cung cấp" | `hub-summary.total_suppliers` |
| Nhập hàng | "{draft_receipts_count} phiếu chờ" | `hub-summary.draft_receipts_count` |
| Trả hàng | "Xử lý trả hàng" (tĩnh) | — (xem 2.5) |
| Nhóm hàng | "Quản lý nhóm hàng" (tĩnh) | — |
| Lịch sử nhập | "Xem chi tiết" (tĩnh) | — |
| Hóa đơn | "Xem lịch sử bán" (tĩnh) | — |
| Báo cáo | "Xem tổng quan" (tĩnh) | — |

Số hiển thị dùng dấu chấm phân cách hàng nghìn kiểu Việt Nam (vd "1.234").

### 2.5. Vì sao "Trả hàng" không có số liệu thật

Đã kiểm tra `backend/modules/sales/return_service.py`: `ReturnOrder` được tạo với `status="COMPLETED"` ngay khi tạo — **không có trạng thái "chờ xử lý"**. Vì vậy không có khái niệm "phiếu chờ" cho trả hàng như ảnh mẫu ban đầu. Quyết định: dùng caption tĩnh "Xử lý trả hàng". (Nếu sau này cần số liệu thật cho card này, ví dụ "X trả hàng hôm nay", sẽ là một yêu cầu riêng.)

### 2.6. Xử lý lỗi tải số liệu

Nếu gọi API `hub-summary` thất bại (mất mạng, lỗi server...): **toàn bộ 5 card có số liệu thật đều âm thầm rơi về caption tĩnh mô tả** (vd Sản phẩm → "Xem danh sách", Tồn kho → "Xem tồn kho"...). **Không hiện `ErrorDialog`** — đây là thông tin trang trí phụ trợ, không phải luồng nghiệp vụ, không đáng để chặn người dùng bằng dialog lỗi.

---

## 3. Backend — API mới

### 3.1. Endpoint

```
GET /api/v1/reports/hub-summary
```

Đặt trong module `report` (cùng chỗ với `/reports/dashboard`), tái dùng pattern đếm sắp/hết hàng đã có trong `report_service.dashboard()`.

**Auth:** yêu cầu đăng nhập (`get_current_user`), **không role-gate** — mọi số liệu ở đây (số SP/KH/NCC/phiếu nhập chờ/cảnh báo tồn kho) không phải dữ liệu tiền bạc/giá vốn nên cả OWNER và CASHIER đều xem được (đúng bảng phân quyền hiện có).

**Response (200):**
```json
{
  "total_products": 1234,
  "low_stock_count": 12,
  "out_of_stock_count": 2,
  "total_customers": 87,
  "total_suppliers": 15,
  "draft_receipts_count": 3
}
```

### 3.2. Logic đếm (theo tenant_id hiện tại, BẮT BUỘC filter tenant)

- `total_products`: `COUNT(*) FROM products WHERE tenant_id=? AND deleted_at IS NULL AND status='ACTIVE'`
- `low_stock_count`, `out_of_stock_count`: tái dùng chính xác logic đã có trong `report_service.dashboard()` (anchor trên `Product` LEFT JOIN `Inventory`, điều kiện `min_stock > 0 AND qty <= min_stock`; out_of_stock là tập con `qty <= 0`).
- `total_customers`: `COUNT(*) FROM customers WHERE tenant_id=? AND deleted_at IS NULL`
- `total_suppliers`: `COUNT(*) FROM suppliers WHERE tenant_id=? AND deleted_at IS NULL`
- `draft_receipts_count`: `COUNT(*) FROM goods_receipts WHERE tenant_id=? AND status='DRAFT'`

### 3.3. Test backend

- Unit/service test: seed dữ liệu 2 tenant, xác nhận từng số đếm đúng và **tenant A không thấy số liệu tenant B** (theo checklist migration của CLAUDE.md).
- Router test: gọi endpoint với user CASHIER và OWNER, xác nhận cả hai đều nhận đủ 6 field (không bị ẩn field nào).

---

## 4. Android — tích hợp

### 4.1. DTO & API client

- `HubSummaryDto` (mới, trong `core/network/dto/ReportDtos.kt`): 6 field khớp response trên (dùng `@SerialName` snake_case → camelCase, theo đúng convention các DTO khác).
- `ReportApi`: thêm `@GET("reports/hub-summary") suspend fun hubSummary(): HubSummaryDto`.
- `ReportRepository`: thêm `open suspend fun hubSummary(): ApiResult<HubSummaryDto>` (theo đúng pattern `dashboard()` hiện có).

### 4.2. HubViewModel

- Inject `ReportRepository` + `ResProvider` (interface đã có sẵn trong `core/i18n`, dùng `AndroidResProvider` ở runtime, `FakeResProvider` trong test).
- Gọi `hubSummary()` một lần khi Hub load (giống pattern `LaunchedEffect(Unit) { viewModel.load() }` các màn khác).
- Expose `HubUiState` chứa `summary: HubSummaryDto?` (null = đang tải hoặc lỗi → mọi card dùng caption tĩnh).
- **Hàm thuần tách riêng để unit-test được** (theo đúng mô hình `stockLevel()` đã dùng ở việc trước):
  ```kotlin
  fun captionFor(route: String, summary: HubSummaryDto?, res: ResProvider): String
  ```
  Nhận route của card + summary (có thể null) + ResProvider, trả về chuỗi caption cuối cùng (số liệu thật hoặc caption tĩnh tương ứng). Test bằng `FakeResProvider` giống các ViewModel test khác trong dự án — không cần Robolectric/Context thật.

### 4.3. HubScreen.kt

- Sửa `HubItem`/`hubGroups`: đổi cấu trúc nhóm theo mục 2.2; xóa nhóm cũ.
- `HubCard`: nhận thêm tham số `caption: String`, hiển thị dòng thứ 3; áp kích thước mới ở mục 2.3.
- Header: đổi từ `AppHeader(title = stringResource(core_hub_title))` sang chuỗi chào ghép theo `user.role`. Slot `actions` đổi từ `TextButton("Đăng xuất")` sang `IconButton(Icons.Outlined.Settings)` + `DropdownMenu` (state `showSettingsMenu` cục bộ) chứa 2 `DropdownMenuItem`: "Đổi mật khẩu" (gọi `onNavigate(Routes.CHANGE_PASSWORD)`) và "Đăng xuất" (set `showLogoutConfirm = true`, giữ nguyên `AlertDialog` xác nhận hiện có).
- Thêm chuỗi mới vào `strings_core.xml`: 3 tên nhóm mới, 2 dòng chào theo vai trò, mô tả icon cài đặt (content description), các caption tĩnh liệt kê ở mục 2.4, mẫu câu cho caption động (vd `"%1$s sản phẩm · %2$s sắp hết"`).

---

## 5. Ngoài phạm vi (KHÔNG làm)

- Không đổi màu sắc/theme (vẫn đơn sắc như hiện tại).
- Không đổi navigation/route của bất kỳ card nào.
- Không thêm số liệu thật cho "Trả hàng" (lý do ở mục 2.5).
- Không cache/làm mới định kỳ số liệu hub-summary (chỉ tải khi vào màn Hub, giống hành vi `dashboard()` ở Báo cáo).
- Không đổi màn Báo cáo, POS, hay bất kỳ màn con nào khác.

---

## 6. Rủi ro & lưu ý

- **Card cao đồng nhất:** vì mọi card đều có dòng phụ (kể cả caption tĩnh 1 dòng ngắn), chiều cao 84dp phải đủ cho 3 dòng — cần kiểm tra thực tế trên máy nhỏ (font scale lớn) không bị tràn chữ; nếu tràn, ưu tiên `maxLines = 1` + `ellipsis` cho dòng phụ thay vì tăng chiều cao.
- **Không phá vỡ role-gating:** Báo cáo vẫn `ownerOnly = true`, không đổi.
- **Số liệu có thể "cũ" một nhịp:** nếu Hub không bị recreate khi quay lại từ màn con (vd vừa thêm SP mới), số "1.234 sản phẩm" có thể chưa cập nhật ngay — chấp nhận được vì đây là thông tin tổng quan trang trí, giống cách `ReportScreen` dashboard hoạt động.

---

## 7. Tiêu chí hoàn thành

- [ ] Backend: endpoint `GET /reports/hub-summary` trả đúng 6 field, có test tenant-isolation.
- [ ] Android: `HubSummaryDto` + `ReportApi.hubSummary()` + `ReportRepository.hubSummary()`.
- [ ] `captionFor()` là hàm thuần, có unit test cho mọi nhánh (đủ hàng/sắp hết/hết hàng, có/không có summary, mọi route tĩnh).
- [ ] `HubScreen` hiển thị đúng 3 nhóm mới (KHÁC chỉ còn Hóa đơn + Báo cáo), đúng thứ tự card, card đã thu nhỏ theo mục 2.3, dòng chào theo vai trò.
- [ ] Header: icon Cài đặt thay cho nút Đăng xuất; mở đúng 2 mục (Đổi mật khẩu, Đăng xuất); Đăng xuất vẫn qua `AlertDialog` xác nhận như cũ.
- [ ] Không còn card "Đổi mật khẩu" trong nhóm KHÁC.
- [ ] API lỗi → card rơi về caption tĩnh, không hiện `ErrorDialog`.
- [ ] Build & test pass (`./gradlew :app:testDebugUnitTest`, `./gradlew :app:assembleDebug`); backend test pass.
