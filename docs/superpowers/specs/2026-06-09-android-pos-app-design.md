# Thiết kế — App Android thay máy POS (Nhập hàng & Bán hàng)

- **Ngày:** 2026-06-09
- **Trạng thái:** Đã chốt qua brainstorming, chờ review trước khi lập plan
- **Phạm vi:** App Android native, online-only, gọi REST API FastAPI sẵn có. Backend chỉ thêm endpoint mobile auth, không đổi schema DB.

## 1. Mục tiêu & bối cảnh

Thay thiết bị POS chuyên dụng bằng điện thoại Android cho chủ shop / thu ngân, phục vụ **bán hàng** và **nhập hàng** (kèm tra cứu tồn và báo cáo nhanh). Backend (FastAPI) và frontend web (React) đã ổn định; app Android là **client mới hoàn toàn**, không tái dùng React FE.

### Quyết định nền tảng (đã chốt)

| Hạng mục | Quyết định | Ghi chú |
|---|---|---|
| Nền tảng | Native Kotlin | App mới, gọi REST `/api/v1` |
| Stack nội bộ | Jetpack Compose + MVVM + Hilt + Retrofit | Chuẩn Android hiện đại |
| Mạng | Online-only | Không offline/sync engine |
| Quét mã | Camera ML Kit + súng bluetooth/USB (HID) | Cả hai |
| In bill | Máy in nhiệt bluetooth 58mm (ESC/POS) | Có fallback bitmap cho tiếng Việt |
| Phạm vi v1 | Bán hàng · Nhập hàng · Tra cứu tồn · Báo cáo nhanh | |
| Auth | Thêm endpoint `/auth/mobile/*` (token trong body) | Tái dùng `auth_service` |

### Không làm ở v1 (YAGNI)

- Offline / sync (online-only).
- Tái dùng/wrap React FE (PWA, Capacitor, React Native).
- Google Play release (v1 phát hành APK trực tiếp; Play để phase sau).
- Đa kho, biến thể SP, khuyến mãi — theo đúng scope phase 1 của hệ thống.

## 2. Kiến trúc tổng thể

Luồng dữ liệu một chiều:

```
Composable (UI)  ──event──▶  ViewModel  ──▶  Repository  ──▶  ApiService (Retrofit)
     ▲                          │                                    │
     └──────StateFlow<UiState>──┘                          FastAPI REST (/api/v1)
```

- Mỗi màn hình có 1 `ViewModel` giữ `StateFlow<UiState>` (loading/success/error).
- `Repository` gọi `ApiService` (Retrofit), trả `ApiResult<T>`.
- Hilt cung cấp dependency (network, repository, auth, hardware).
- App là 1 module Android riêng trong repo (`android/`), tách hẳn `frontend/`.

### Cấu trúc thư mục

```
android/
├── app/
│   ├── src/main/java/com/mykiot/pos/
│   │   ├── MyKiotApp.kt              # @HiltAndroidApp
│   │   ├── core/
│   │   │   ├── network/              # Retrofit, OkHttp, AuthInterceptor, TokenAuthenticator, ErrorMapper
│   │   │   ├── auth/                 # TokenStore (EncryptedSharedPreferences), AuthRepository
│   │   │   ├── di/                   # Hilt modules
│   │   │   ├── ui/                   # theme, component dùng chung (định dạng VND, hộp lỗi VN)
│   │   │   └── hardware/             # BarcodeScanner (ML Kit), EscPosPrinter (bluetooth)
│   │   ├── feature/
│   │   │   ├── auth/                 # login screen + VM
│   │   │   ├── pos/                  # bán hàng: cart, payment, draft
│   │   │   ├── receipt/              # nhập hàng (goods receipt)
│   │   │   ├── inventory/            # tra cứu tồn + kardex
│   │   │   └── report/               # dashboard/EOD nhanh
│   │   └── navigation/               # NavHost, routes
│   └── build.gradle.kts
├── gradle/ ...
└── README.md
```

**Nguyên tắc:** mỗi `feature/` tự chứa (screen + viewmodel + repository + dto), giao tiếp ra ngoài qua `core/network` + `core/auth`. ViewModel test được độc lập bằng fake repository.

### Tiếng Việt (bắt buộc, theo CLAUDE.md)

Mọi thông báo lỗi/validation/toast hiển thị cho người dùng **bằng tiếng Việt**. Gom 1 `ErrorMapper`: đọc body lỗi `{"error":{"code","message"}}` của backend → ưu tiên `message` (đã tiếng Việt từ BE), fallback map theo `code` khi cần. `error.code` giữ nguyên UPPER_SNAKE_CASE.

## 3. Auth & Networking

### 3.1 Backend — thêm endpoint mobile

Tách khỏi luồng cookie của web, **không phá web hiện tại**, tái dùng nguyên `auth_service` (service đã sẵn trả `refresh_token` trong result — web chỉ loại nó khỏi response để set cookie).

```
POST /api/v1/auth/mobile/login     body: {phone|email, password}
                                   → 200 {access_token, refresh_token, user, tenant}
POST /api/v1/auth/mobile/refresh   body: {refresh_token}
                                   → 200 {access_token, refresh_token}
POST /api/v1/auth/mobile/logout    body: {refresh_token}  → revoke
```

- Khác biệt duy nhất so với web: trả token trong **body** thay vì `set_refresh_cookie`; refresh/logout nhận token từ **body** thay vì `Cookie`.
- Giữ nguyên: refresh token rotation, family-based reuse-detection, brute-force lock (`failed_login_count` / `locked_until`), slowapi rate limit.
- Không đổi schema DB.

### 3.2 App — token & interceptor

- `TokenStore`: lưu access + refresh token trong **EncryptedSharedPreferences** (mã hoá tại thiết bị); access token cache thêm trong memory.
- `AuthInterceptor` (OkHttp): gắn `Authorization: Bearer <access>` + `X-Requested-With: XMLHttpRequest` cho mọi request.
- `TokenAuthenticator` (OkHttp): khi **401** → gọi `/auth/mobile/refresh` với **single-flight** (mutex, tránh 2 request 401 cùng lúc refresh 2 lần) → lưu token mới → retry request gốc. Refresh thất bại → xoá token, điều hướng về Login.
- `BASE_URL` qua `BuildConfig`: debug → server dev, release → prod HTTPS.

### 3.3 Error handling

- `ApiResult<T>` = `Success(data)` | `Error(code, messageVN)`.
- Mất mạng / timeout → "Mất kết nối mạng, vui lòng thử lại".
- Lỗi 4xx/5xx → qua `ErrorMapper`.

## 4. Các luồng tính năng (v1)

Navigation: **Bottom nav 4 tab** — Bán · Nhập · Tồn · Báo cáo. Màn Login tách riêng ngoài nav.

### 4.1 Bán hàng (POS) — cốt lõi

- **Tìm/quét SP:** ô tìm gọi `GET /products/search?q=` (tên/SKU/barcode); nút camera → ML Kit trả barcode → `GET /products/barcode/{code}` (nhận `matched_unit` nếu là barcode đơn vị); súng ngoài gõ vào chính ô tìm (kết thúc bằng Enter).
- **Giỏ hàng:** danh sách dòng — sửa số lượng (DECIMAL, hỗ trợ bán cân), sửa giá, giảm giá dòng; tổng tiền realtime.
- **Khách hàng:** `GET /customers/phone/{phone}` hoặc bỏ trống (khách vãng lai).
- **Tạo & hoàn tất:** `POST /invoices` (DRAFT) → `POST /invoices/{id}/complete` với payments đa phương thức (CASH/BANK_TRANSFER/MOMO/VNPAY). Hiển thị tiền thối.
- **Treo hoá đơn:** để DRAFT; danh sách treo qua `GET /invoices/drafts`.
- **Sau complete:** render bill 58mm → in bluetooth (mục 5), có nút "In lại".

### 4.2 Nhập hàng (Goods Receipt)

- Chọn NCC (`GET /suppliers`), quét/tìm SP thêm dòng (số lượng + giá vốn + đơn vị), tổng tiền.
- `POST /goods-receipts` (DRAFT) → `POST /goods-receipts/{id}/complete`. Backend tự cộng tồn + tính giá vốn bình quân; **client không tự tính lại tồn**.

### 4.3 Tra cứu tồn kho

- `GET /inventory` (phân trang + tìm), badge hàng sắp hết `GET /inventory/low-stock`.
- Chi tiết SP → thẻ kho (kardex) `GET /inventory/{product_id}/movements`.

### 4.4 Báo cáo nhanh

- `GET /reports/dashboard` (doanh thu hôm nay, số đơn). Chỉ đọc, hiển thị card.
- Chốt ca cuối ngày: `GET /reports/end-of-day?date=` — **OWNER only** (backend chặn). Với CASHIER, ẩn mục này khỏi tab Báo cáo.

### 4.5 Phân quyền (UX)

- App dùng đúng quyền backend theo `role` trong JWT — backend là nguồn chặn thật.
- App **ẩn/disable** nút thao tác OWNER khi role = CASHIER (hủy hóa đơn COMPLETED, điều chỉnh tồn, báo cáo lợi nhuận) cho gọn UX.
- Giá vốn hiển thị theo `tenant.settings.show_cost_to_cashier`.

## 5. Phần cứng

### 5.1 Quét mã vạch

- **Camera (ML Kit):** module `BarcodeScanner` dùng CameraX + ML Kit `barcode-scanning` (on-device). Overlay quét, nhận EAN-13/CODE-128 → trả chuỗi về ViewModel → gọi API lookup. Xin quyền `CAMERA` runtime; fallback nhập tay.
- **Súng ngoài (bluetooth/USB-OTG):** hoạt động như bàn phím HID (gõ barcode + Enter). App giữ một ô input luôn focus ở màn Bán/Nhập để hứng; nhận Enter → xử lý như vừa quét. Không cần thư viện riêng.

### 5.2 In bill nhiệt 58mm (ESC/POS bluetooth)

- Module `EscPosPrinter`: kết nối **Bluetooth Classic (SPP)**, gửi byte ESC/POS. Dùng thư viện ESC/POS Android phổ biến (vd `DantSu/ESCPOS-ThermalPrinter-Android`).
- **Layout bill 58mm (32 ký tự/dòng):** tên shop + địa chỉ/SĐT (tenant), mã HĐ + ngày giờ (giờ VN `Asia/Ho_Chi_Minh`), danh sách SP (tên / SL×đơn giá / thành tiền), tổng tiền, tiền khách trả + thối, `receipt_footer` từ `tenant.settings`.
- **Tiếng Việt có dấu:** nếu máy in không sẵn font Việt → render dòng thành **bitmap** rồi in (fallback an toàn).
- **Luồng:** Cài đặt → chọn & nhớ máy in (lưu MAC trong prefs). Sau complete → tự in + nút "In lại". Quyền `BLUETOOTH_CONNECT` (Android 12+) runtime. Máy in chưa kết nối → báo lỗi VN, vẫn hiển thị bill trên màn.

## 6. Build, phân phối & Testing

### Build & config

- Gradle Kotlin DSL, `minSdk 26` (Android 8.0+), `targetSdk 35`.
- 2 build type: `debug` (BASE_URL dev), `release` (BASE_URL prod HTTPS, bật minify/R8, ký APK release).
- Secrets/URL qua `BuildConfig` + `local.properties` (không commit).

### Phân phối

- v1: **APK trực tiếp** (cài tay/qua link) cho 5-50 shop.
- Google Play Internal Testing để ngỏ phase sau.

### Testing

- **Unit ViewModel** (JUnit + Turbine + MockK): state loading/success/error, validate giỏ hàng, tính tổng tiền, tiền thối, validate phiếu nhập.
- **Repository:** map API ↔ DTO; `ErrorMapper` ra đúng message VN.
- **Auth:** `TokenAuthenticator` refresh single-flight; 401 → refresh → retry; refresh fail → logout.
- **Hardware:** tách interface (`Scanner`, `Printer`) để test logic không cần thiết bị thật; smoke test thủ công với máy in/súng thật (checklist QA).
- **Backend:** thêm test cho `/auth/mobile/*` (login trả token body, refresh rotation, reuse-detection) bên cạnh test cookie hiện có.

## 7. Backend đổi gì (tổng kết)

Chỉ thêm `POST /api/v1/auth/mobile/login | refresh | logout`, tái dùng `auth_service`. **Không** đổi schema DB, **không** phá luồng web.

## 8. Rủi ro & lưu ý

- **Cookie Secure vs native:** đã tránh bằng endpoint mobile trả token body — không phụ thuộc cookie.
- **In tiếng Việt 58mm:** một số máy in không có font Việt → bắt buộc fallback bitmap (đã tính trong mục 5.2).
- **Súng HID + ô focus:** cần đảm bảo ô hứng barcode luôn giữ focus ở màn Bán/Nhập, tránh ký tự rơi vào field khác.
- **Quyền runtime:** CAMERA + BLUETOOTH_CONNECT (Android 12+) cần xin đúng thời điểm, có UX khi bị từ chối.
