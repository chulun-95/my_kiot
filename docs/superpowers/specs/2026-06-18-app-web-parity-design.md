# Spec: Đồng bộ chức năng App (Android) ↔ Web + sửa lỗi UX

Ngày: 2026-06-18 · Branch: fix/return-debt-business-logic

## Bối cảnh

App Android (Jetpack Compose) đang thiếu một số chức năng so với web và có vài lỗi UX
tại quầy. Mục tiêu: vá lỗi + bù chức năng, **giữ màn chính gọn** — chức năng chính luôn
hiển thị đủ, thông tin phụ ẩn sau nút `+` / dialog / vùng mở rộng.

Mọi thông báo cho người dùng dùng **tiếng Việt** (theo CLAUDE.md).

## 8 mục công việc

### 1. Sửa ô nhập tiền (MoneyInput) — lỗi "16 → 1000"
- **File:** `core/ui/MoneyInput.kt` (+ `CostField` trong `feature/receipt/ReceiptLineRow.kt`).
- **Nguyên nhân:** dùng `OutlinedTextField`/`BasicTextField` với value `String`, con trỏ không
  ghim về cuối → chữ số gõ vào lọt giữa chuỗi, `applyMoneyEdit` lấy nhầm "chữ số cuối".
- **Sửa:** chuyển sang `TextFieldValue`, luôn đặt `selection` về cuối sau mỗi thay đổi.
  Giữ nguyên kiểu máy tính tiền (mỗi chữ số ×100) như web `MoneyInput.tsx`.
- **Kỳ vọng:** gõ `1`→100, `1,6`→1.600, `1,6,0`→16.000. Logic `applyMoneyEdit` giữ nguyên,
  test `MoneyTest` vẫn xanh.

### 2. POS — Quét liên tục (camera 1/3 trên, giỏ 2/3 dưới)
- **File:** `core/hardware/scanner/MlKitScannerScreen.kt`, `feature/pos/PosScreen.kt`.
- Tách scanner thành bản **nhúng** `EmbeddedScanner(onScanned)` (callback **nhiều lần**,
  có debounce bỏ qua cùng mã trong ~1.5s) + giữ overlay cũ cho các màn khác.
- PosScreen thêm chế độ quét liên tục: bấm icon quét → camera chiếm **1/3 trên**, danh sách
  SP đã thêm **2/3 dưới**, nút **"Hoàn tất"** thoát về màn list bình thường.
- Camera **không đóng** sau mỗi lần quét.

### 3. POS — Âm báo quét
- **File:** `MlKitScannerScreen.kt`, `feature/pos/PosViewModel.kt`, `feature/receipt/ReceiptViewModel.kt`.
- Bỏ `Beeper.pip()` phát ngay khi *thấy* mã (đang gây pip+pipip lẫn lộn khi mã lạ).
- `pip` = SP tìm thấy & thêm vào giỏ thành công; `pipip` (`Beeper.error()`) = không tìm thấy / hết tồn.

### 4. POS — Chọn khách hàng (nút `+`)
- **File:** `feature/pos/PosScreen.kt` + dialog mới `CustomerPickerDialog.kt`; ViewModel đã có `setCustomer`.
- Chip khách gọn đầu giỏ: mặc định "Khách lẻ" + nút **`+ Khách`**.
- Dialog tìm theo tên/SĐT (`CustomerApi.list(search)`), chọn / **+ Thêm KH nhanh** (`CustomerApi.create`).
  Đã chọn → hiện tên + nút `×` để bỏ. Cần thêm `PosRepository.searchCustomers()`.

### 5. POS — Giảm giá hoá đơn / từng dòng
- **File:** `feature/pos/PosScreen.kt`, `feature/pos/CartLineRow.kt`; ViewModel đã có
  `setUnitPrice`, `setLineDiscount`, `cart.invoiceDiscount`.
- Giảm cả hoá đơn: ô tiền gọn trong thẻ "Tổng cộng".
- Giá/giảm từng dòng: bấm dòng → dialog nhỏ chỉnh **đơn giá** + **giảm dòng** (row chính vẫn gọn).

### 6. Nhập hàng — Tiền trả + luồng "Lưu nháp → Hoàn tất"
- **File:** `feature/receipt/ReceiptScreen.kt`, `ReceiptViewModel.kt`, `ReceiptRepository.kt`,
  `core/network/InventoryApi.kt`, route mới + màn `GoodsReceiptDetailScreen.kt`.
- Form thêm: ô **"Tiền trả"** (mặc định = tổng) + nút **"Trả đủ"**, **phương thức TT**
  (hiện khi tiền trả > 0), **ghi chú**. NCC không bắt buộc khi trả đủ.
- Nút "Hoàn tất nhập" → **"Lưu phiếu nháp"** (tạo DRAFT) → mở **màn Chi tiết phiếu nhập** có
  nút **"Hoàn tất nhập"** (gọi `completeReceipt`). Tách `ReceiptRepository.submit` thành
  `createDraft` + `complete`. Thêm `InventoryApi.getReceipt(id)` + route `RECEIPT_DETAIL`.
- Sửa lỗi gốc: trả đủ → không thành nợ → không bị ép chọn NCC.

### 7. Xác nhận khi xoá
- **File:** `core/ui/ConfirmDialog.kt` (mới, dùng chung) + các nút xoá.
- Áp dụng: xoá dòng giỏ POS (khi SL về 0 hoặc nút xoá), xoá dòng nhập hàng (icon thùng rác).

### 8. Sửa hiển thị số lượng (tồn kho / thẻ kho)
- **File:** `core/util/Money.kt` thêm `formatQty()`; áp dụng `InventoryScreen.kt`,
  `MovementsDialog.kt`, và rà các chỗ in chuỗi số lượng decimal thô.
- `formatQty`: parse BigDecimal → bỏ 0 thừa, `,` cho thập phân, `.` cho hàng nghìn (kiểu VN).
  `1.000`→"1", `1.500`→"1,5", `0.300`→"0,3", `1200`→"1.200".

## Quyết định / phạm vi
- Ô nhập tiền: GIỮ kiểu máy tính tiền (khớp web), chỉ sửa lỗi con trỏ.
- Nhập hàng: theo web — 2 bước Lưu nháp → Hoàn tất (cần màn chi tiết mới).
- Không đụng backend/web; chỉ sửa app Android.

## Kiểm thử
- Unit: `MoneyTest` (giữ xanh), thêm test `formatQty`, test debounce scan nếu tách được logic.
- Build `./gradlew assembleDebug` + `testDebugUnitTest` xanh trước khi xong.
