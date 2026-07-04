# Thiết kế: Làm mới giao diện MyKiot POS (Android)

**Ngày:** 2026-07-04
**Trạng thái:** Đã duyệt hướng thiết kế, chờ review spec
**Phạm vi:** App Android (`android/app/src/main/java/com/mykiot/pos`)

---

## 1. Mục tiêu & nguyên tắc

Nâng cấp giao diện app cho **chuyên nghiệp hơn** theo hướng **POS thương mại có màu**, dựa trên màu thương hiệu **teal**.

**Nguyên tắc bất di bất dịch:**
- **Giữ nguyên 100% chức năng** — không thêm/bớt tính năng, use case, luồng nghiệp vụ.
- **Giữ nguyên cấu trúc** — không thêm/bớt/gộp màn hình, route, navigation.
- **Không đụng tầng logic** — ViewModel, data layer, DTO, API client giữ nguyên.
- Chỉ thay **lớp trình bày**: theme, token màu, component dùng chung, cách áp màu.
- Tuân thủ quy ước dự án: mọi text tiếng Việt; lỗi hiển thị bằng `ErrorDialog` (icon theo loại lỗi + mô tả + nút Đóng), **không** dùng toast/snackbar cho lỗi.
- App hiện chỉ có **light mode** → giữ nguyên, không thêm dark mode.

**Quyết định đã chốt (qua brainstorm trực quan):**
1. Hướng thẩm mỹ: **POS thương mại đầy đủ màu**.
2. Màu thương hiệu: **Teal (xanh ngọc)** — vibe bán lẻ VN, đáng tin.
3. Hub: **icon tile màu nhạt (soft)** — thẻ trắng viền mảnh, ô icon nền teal nhạt.
4. Danh sách: **kiểu gạch phân cách (divider list)** — gọn, nhiều dòng/màn, quét nhanh.
5. Hệ màu trạng thái ngữ nghĩa đã duyệt (xem mục 2.2).

---

## 2. Design tokens

### 2.1. Màu — `core/ui/theme/Color.kt`

Giữ nền trung tính hiện có (`Paper`, `PaperGray`, `PaperGrayDark`, `Line`, `LineSoft`, `Ink`, `InkSoft`). **Thêm** nhóm màu thương hiệu teal + màu trạng thái:

```kotlin
// ---- Thương hiệu teal ----
val Brand        = Color(0xFF0D9488) // teal-600 — primary, nút chính, tab active
val BrandDark    = Color(0xFF0F766E) // teal-700 — nhấn đậm, gradient, viền nút phụ
val BrandSoft    = Color(0xFFCCFBF1) // teal-100 — nền icon tile, badge info
val BrandOnSoft  = Color(0xFF0F766E) // chữ/icon trên nền BrandSoft

// ---- Màu trạng thái ngữ nghĩa (nền nhạt + chữ đậm) ----
val StatusOkBg     = Color(0xFFDCFCE7); val StatusOkFg     = Color(0xFF15803D) // Đã thanh toán / Còn hàng
val StatusWarnBg   = Color(0xFFFEF3C7); val StatusWarnFg   = Color(0xFFB45309) // Bán nợ / Sắp hết
val StatusDangerBg = Color(0xFFFEE2E2); val StatusDangerFg = Color(0xFFB91C1C) // Đã hủy / Hết hàng
val StatusMutedBg  = Color(0xFFF1F5F9); val StatusMutedFg  = Color(0xFF475569) // Nháp / Treo
val StatusInfoBg   = BrandSoft;         val StatusInfoFg   = BrandOnSoft        // Thông tin / nhấn phụ
```

Giữ nguyên nhóm `Data*` (màu biểu đồ) — đã hợp tông teal/green/sky/violet/amber.

### 2.2. Ý nghĩa màu trạng thái (dùng thống nhất toàn app)

| Màu | Ngữ cảnh hóa đơn/phiếu | Ngữ cảnh tồn kho |
|-----|------------------------|------------------|
| 🟢 Success | Đã thanh toán / Hoàn tất | Còn hàng |
| 🟡 Warning | Bán nợ (paid < total) | Sắp hết (≤ min_stock) |
| 🔴 Danger | Đã hủy | Hết hàng (= 0) |
| ⚪ Muted | Nháp (DRAFT) / Treo | — |
| 🩵 Info | Nhấn phụ / nhãn thông tin | — |

### 2.3. ColorScheme — `core/ui/theme/Theme.kt`

Đổi `MonoLight` → `TealLight`:
- `primary = Brand`, `onPrimary = Paper`
- `primaryContainer = BrandSoft`, `onPrimaryContainer = BrandDark`
- `secondary = BrandDark`
- `error = StatusDangerFg`, `onError = Paper`, `errorContainer = StatusDangerBg`, `onErrorContainer = StatusDangerFg` (thay vì đen như hiện tại)
- Các slot nền/viền (`background`, `surface`, `surfaceVariant`, `outline`…) giữ nguyên giá trị trung tính hiện có.

Hàm `MyKiotTheme` giữ nguyên chữ ký, chỉ trỏ tới `TealLight`.

### 2.4. Typography — `core/ui/theme/Type.kt`

Giữ nguyên (`MonoTypography` đã tốt: tiêu đề đậm, letter-spacing chặt). Đổi tên gọi không bắt buộc.

### 2.5. Spacing

Giữ nguyên `Spacing` object.

---

## 3. Component dùng chung — `core/ui/`

| Component | Thay đổi |
|-----------|----------|
| `StatusBadge` (mới) | Enum `Success/Warning/Danger/Neutral/Info` → nền nhạt + chữ đậm. Thay thế cách dùng badge trạng thái rải rác. |
| `MonoBadge` | Giữ lại (alias/không xóa) để không vỡ chỗ đang gọi; hoặc refactor nội bộ gọi `StatusBadge`. |
| `AppSearchField` | Viền + cursor focus màu teal; slot trailing (quét mã) render dạng nút tròn teal. |
| `ListRow` (mới) | Hàng danh sách chuẩn: leading (emoji/thumbnail/ảnh), tiêu đề + phụ đề, trailing (giá + `StatusBadge`), gạch phân cách dưới. Tham số hóa để tái dùng. |
| `AppTextField` | Focus/label màu teal (đang là đen). |
| Nút chính | Chuẩn hóa: fill teal + bóng mềm, bo 14dp. Nút phụ: viền teal, chữ teal. |
| `KpiTile` | Accent số/nhấn về teal. |
| `ChartCard` | Accent về teal (tiêu đề/đường nhấn). |
| `AppHeader`, `SectionHeader`, dialogs (`ConfirmDialog`, `ErrorDialog`, `LoadingDialog`), `QtyStepper`, `MoneyInput` | Giữ cấu trúc; chỉ đồng bộ màu nhấn sang teal nơi có. `ErrorDialog` giữ nguyên hành vi (không đổi thành toast). |

---

## 4. Áp dụng theo màn (chỉ đổi trình bày)

Không màn nào đổi logic/ViewModel. Chỉ thay style + dùng component mới.

| Màn | Thay đổi trình bày |
|-----|--------------------|
| **Hub** (`navigation/HubScreen.kt`) | `HubCard`: ô icon nền teal nhạt (soft tile). `PosButton`: teal + bóng. Group header giữ nguyên. |
| **POS** (`feature/pos/PosScreen.kt`) | Theo mockup đã duyệt: nút quét tròn teal, nút Thanh toán teal (bóng), Treo đơn viền teal, giỏ hàng divider + stepper, badge "đơn treo" teal nhạt, tổng tiền in đậm. Cấu trúc giữ nguyên. |
| **Sản phẩm** (`ProductListScreen`, `ProductDetailScreen`, `AddProductScreen`) | List dùng `ListRow` + badge tồn kho (Còn/Sắp hết/Hết). Form field teal. Detail: header + badge + nút theo hệ mới. |
| **Tồn kho** (`InventoryScreen`) | `ListRow` + badge tồn kho. |
| **Hóa đơn** (`InvoiceListScreen`, chi tiết) | `ListRow` + `StatusBadge` (Đã TT/Bán nợ/Đã hủy/Nháp). |
| **Trả hàng** (`ReturnsScreen`, `ReturnFormScreen`) | Badge + nút theo hệ mới. |
| **Phiếu nhập** (`GoodsReceiptListScreen`, `GoodsReceiptDetailScreen`, `ReceiptScreen`) | `ListRow` + badge trạng thái phiếu; form teal. |
| **Khách hàng** (`CustomerListScreen`, `CustomerDetailScreen`, `AddCustomerScreen`) | `ListRow`; form teal. |
| **Nhà cung cấp** (`SupplierListScreen`, `AddSupplierScreen`) | `ListRow`; form teal. |
| **Nhóm hàng** (`CategoryTreeScreen`) | Đồng bộ màu nhấn teal. |
| **Báo cáo** (`ReportScreen`) | `KpiTile` + `ChartCard` accent teal. |
| **Đăng nhập** (`LoginScreen`) | Field focus teal, nút đăng nhập teal + bóng. |
| **Đổi mật khẩu** (`ChangePasswordScreen`) | Field + nút teal. |
| **Tài khoản** (`feature/account`) | Đồng bộ màu nhấn. |

---

## 5. Ngoài phạm vi (KHÔNG làm)

- Không thêm/bớt/đổi màn hình, route, navigation.
- Không thêm/bớt tính năng hay use case.
- Không sửa ViewModel, data layer, DTO, network, business logic.
- Không thêm dữ liệu/KPI mới vào Hub (giữ đúng nội dung hiện tại).
- Không thêm dark mode.
- Không đổi backend/web.

---

## 6. Rủi ro & lưu ý

- **Rò rỉ màu cũ:** một số màn hardcode màu đen/`onSurface` cho nút thay vì dùng `primary`. Khi áp teal cần rà soát các chỗ hardcode (`containerColor = ...onSurface`) để nút chính chuyển sang teal đồng bộ (ví dụ nút Thanh toán/Quét trong `PosScreen`).
- **Không vỡ call-site:** giữ `MonoBadge` (không xóa đột ngột) — refactor dần sang `StatusBadge`.
- **Tương phản/A11y:** cặp nền-nhạt/chữ-đậm của màu trạng thái đã chọn đạt độ tương phản đọc tốt; giữ đúng cặp trong bảng 2.2.
- **Kiểm thử trực quan:** sau khi áp, chạy app kiểm tra từng nhóm màn (Hub → POS → List → Form → Report) để đảm bảo không sót màu đơn sắc cũ.

---

## 7. Tiêu chí hoàn thành

- [ ] `Color.kt`/`Theme.kt` có token teal + màu trạng thái; `error` là đỏ thật.
- [ ] `StatusBadge` + `ListRow` tồn tại và được dùng ở các màn danh sách.
- [ ] Hub, POS đúng như mockup đã duyệt.
- [ ] Tất cả màn danh sách/form/detail áp hệ màu mới, không còn nút chính màu đen.
- [ ] Không thay đổi chức năng/logic (diff chỉ nằm ở tầng UI).
- [ ] App build & chạy được; rà soát trực quan từng nhóm màn.
