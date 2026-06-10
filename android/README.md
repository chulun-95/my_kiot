# My Kiot POS — Android app

App Android native (Kotlin + Jetpack Compose + Hilt + Retrofit) thay máy POS cho nhập & bán hàng. Online-only, gọi REST API của backend FastAPI tại `/api/v1`.

Spec: [`../docs/superpowers/specs/2026-06-09-android-pos-app-design.md`](../docs/superpowers/specs/2026-06-09-android-pos-app-design.md)
Plan Phase 1: [`../docs/superpowers/plans/2026-06-09-android-pos-phase1-foundation.md`](../docs/superpowers/plans/2026-06-09-android-pos-phase1-foundation.md)

## Trạng thái

**Đã viết code cả 4 phase (MVP đầy đủ):**
- **Phase 1 — Foundation + Login:** networking + auth (token trong EncryptedSharedPreferences, auto-refresh 401), Đăng nhập tiếng Việt (kể cả multi-tenant), shell 4 tab.
- **Phase 2 — Bán hàng (POS):** tìm/quét SP (camera ML Kit + súng HID), giỏ hàng (+1/gộp), thanh toán đa PT, in bill 58mm ESC/POS.
- **Phase 3 — Nhập hàng:** chọn NCC, quét/tìm SP, sửa SL/giá vốn, tạo+hoàn tất phiếu nhập.
- **Phase 4 — Tồn kho + Báo cáo:** danh sách tồn + tìm + badge sắp hết + thẻ kho (kardex); dashboard hôm nay + chốt ca EOD (OWNER).

> ⚠️ **Toàn bộ code Android chưa được build/test trên máy phát triển ban đầu** (máy đó không có Android SDK). Lần đầu build PHẢI chạy `testDebugUnitTest` + `assembleDebug` và sửa lỗi biên dịch nhỏ nếu có. Tuyến phòng thủ chính là các unit test JVM cho logic thuần (Cart, ReceiptBasket, ReceiptLayout, Money) và các ViewModel (Login/Pos/Receipt/Inventory/Report).

## Yêu cầu môi trường

- JDK 17
- Android SDK (set `ANDROID_HOME` / `sdk.dir` trong `local.properties`)
- Android Studio (khuyến nghị) hoặc Gradle 8.11+

## Thiết lập

1. Copy `local.properties.example` → `local.properties`, sửa `sdk.dir` (và `BASE_URL_*` nếu cần).
2. Sinh Gradle wrapper jar nếu chưa có (repo chỉ commit `gradle-wrapper.properties`, không commit jar):
   ```bash
   gradle wrapper --gradle-version 8.11.1
   ```
   Hoặc mở thư mục `android/` bằng Android Studio — IDE tự tạo wrapper.

## Build & test

```bash
# từ thư mục android/
./gradlew :app:assembleDebug          # build APK debug
./gradlew :app:testDebugUnitTest      # chạy unit test JVM (ErrorMapper, TokenAuthenticator, LoginViewModel, FakeTokenStore)
./gradlew :app:installDebug           # cài lên thiết bị/emulator
```

> ⚠️ Các file Phase 1 được viết sẵn nhưng **chưa được build/test trên máy phát triển ban đầu** (máy đó không có Android SDK). Lần đầu build cần chạy `testDebugUnitTest` + `assembleDebug` và sửa nếu có lỗi biên dịch nhỏ trước khi coi Phase 1 là "done".

## Chạy thử với backend local

```bash
# tại gốc repo
python -m uvicorn backend.main:app --reload --port 8000
```
Emulator Android truy cập backend qua `http://10.0.2.2:8000` (đã là default cho build debug).

## Smoke test thủ công (Phase 1 DoD)

1. Mở app → màn Đăng nhập tiếng Việt.
2. Đăng ký 1 shop (qua web/curl), đăng nhập bằng phone/password → vào Home 4 tab.
3. Sai mật khẩu → lỗi tiếng Việt dưới ô nhập.
4. Tắt & mở lại app → vẫn đăng nhập (token đã lưu) → vào thẳng Home.
