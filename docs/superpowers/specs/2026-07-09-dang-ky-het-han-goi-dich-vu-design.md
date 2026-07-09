# Đăng ký shop + hết hạn gói dịch vụ (6 tháng) — Design

Ngày: 2026-07-09

## 1. Bối cảnh & mục tiêu

Hiện tại `POST /auth/register` đã hoạt động nhưng:
- Form web thu thập `shop_name`, `owner_name` (bắt buộc), `phone`, `email` (tùy chọn), `password` — không có `address`, không có nhập lại mật khẩu.
- Không có khái niệm "hạn dùng dịch vụ" ở đâu trong hệ thống — mọi shop đăng ký xong dùng vĩnh viễn.

**Mục tiêu của tính năng này:**
1. Rút gọn form đăng ký web còn đúng 5 trường: Tên cửa hàng, Số điện thoại, Địa chỉ, Mật khẩu, Nhập lại mật khẩu.
2. Mỗi shop khi đăng ký được cấp hạn dùng 6 tháng kể từ ngày đăng ký (`tenants.created_at`).
3. Khi hạn dùng còn ≤ 7 ngày → hiển thị banner cảnh báo (không chặn thao tác) trên cả web.
4. Khi đã hết hạn → hiển thị popup toàn màn hình **không thể đóng** trên cả web và app Android, chỉ có nút liên hệ Facebook, Zalo, và nút Đăng xuất. Ứng dụng vẫn dùng được về mặt kỹ thuật (backend **không** chặn API) — popup chỉ chặn ở tầng giao diện.
5. Gia hạn được thực hiện thủ công bởi admin (chính là chủ hệ thống) qua 1 script nội bộ chạy trên VPS, không cần xây admin UI hay endpoint có auth riêng.

**Ngoài phạm vi (non-goals):**
- Không xây cổng thanh toán tự động, không tích hợp thanh toán online.
- Không xây trang quản trị (admin dashboard) để gia hạn — dùng script CLI.
- Không lưu lịch sử tất cả các lần gia hạn thành bảng riêng — chỉ ghi 1 dòng `audit_logs` mỗi lần gia hạn (đủ để tra cứu khi cần).
- Không chặn API backend khi hết hạn — chỉ chặn ở tầng hiển thị (web + app).
- Không áp dụng gói dịch vụ khác nhau (basic/pro,...) — chỉ có 1 loại hạn dùng duy nhất cho MVP.

## 2. Data model

Thêm 1 cột vào bảng `tenants` có sẵn (không tạo bảng mới):

```sql
ALTER TABLE tenants ADD COLUMN expires_at TIMESTAMPTZ NULL;
```

- `expires_at = NULL` → không giới hạn (dùng cho tài khoản test/đặc biệt do admin tự set tay nếu cần; **luồng đăng ký thường luôn set `expires_at`**).
- `expires_at <= NOW()` → coi là đã hết hạn.
- "Ngày đăng ký" hiển thị cho người dùng lấy từ `tenants.created_at` có sẵn (`AuditMixin`), không cần cột mới.

Migration mới: `alembic/versions/009_tenant_expiry.py`.

## 3. Backend

### 3.1. `POST /auth/register`

`RegisterRequest` (backend/modules/auth/schemas.py) sửa lại:

```python
class RegisterRequest(BaseModel):
    shop_name: str = Field(min_length=2, max_length=200)
    phone: str
    address: str = Field(min_length=5, max_length=500)
    password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        if not is_valid_phone(v):
            raise ValueError("Số điện thoại không hợp lệ")
        return v

    @field_validator("confirm_password")
    @classmethod
    def _validate_confirm(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Xác nhận mật khẩu không khớp")
        return v
```

Bỏ hẳn `owner_name` và `email` khỏi request. `auth_service.register()`:
- Tạo `Tenant(name=shop_name, address=address, expires_at=now() + relativedelta(months=6))`.
- Tạo `User(role="OWNER", full_name=shop_name.strip(), phone=..., email=None, ...)` — dùng luôn tên shop làm tên hiển thị của chủ tài khoản (chủ shop có thể đổi tên sau này nếu có màn "Thông tin cá nhân"; hiện chưa có nên không cần hỏi thêm ở form đăng ký).
- Các bước còn lại (tạo slug, issue token...) giữ nguyên.

`TenantBrief` (dùng chung cho `RegisterResponse`, `LoginSuccessResponse`, `MeResponse`) bổ sung field:

```python
class TenantBrief(BaseModel):
    id: int
    name: str
    slug: str
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
```

Đây là **nguồn dữ liệu duy nhất** để mọi client (web, app) tự tính trạng thái hết hạn. Không thêm field `is_expired` tính sẵn ở BE — logic so sánh thời gian để ở client (đơn giản, và tránh lệch múi giờ giữa server tính sẵn với thời điểm client hiển thị).

### 3.2. Không đụng vào authorization hiện có

`get_current_user`, `require_role`, và mọi router nghiệp vụ (products, sales, inventory, reports, staff...) **giữ nguyên hoàn toàn** — hết hạn không ảnh hưởng đến việc gọi API. Đây là quyết định đã chốt: chặn chỉ ở tầng hiển thị.

### 3.3. Script gia hạn nội bộ

File mới: `backend/scripts/extend_tenant.py`, chạy tay trên VPS:

```
python -m backend.scripts.extend_tenant --phone 0912345678 --months 6
```

Logic:
1. Tìm `User` theo `phone` (role OWNER, chưa xóa) → lấy `tenant_id`.
2. Lấy `Tenant`, tính `base = tenant.expires_at if tenant.expires_at and tenant.expires_at > now() else now()`.
3. `tenant.expires_at = base + relativedelta(months=months)`.
4. Ghi `audit_logs` — action mới `EXTEND_SUBSCRIPTION` (thêm vào enum trong `backend/shared/audit.py`), `entity_type="tenant"`, `entity_id=tenant.id`, `new_data={"months": months, "new_expires_at": ...}`, `user_id` = id của chủ shop (OWNER) vì audit log yêu cầu `user_id NOT NULL` và không có "admin user" thật trong hệ thống.
5. Commit, in ra console ngày hết hạn mới để admin xác nhận trước khi báo lại khách qua Zalo/Facebook.
6. `--months` mặc định 6 nếu không truyền.

Script dùng thẳng `backend.database` engine/sessionmaker hiện có (không thêm HTTP endpoint, không thêm secret key).

## 4. Web frontend

### 4.1. Form đăng ký (`frontend/src/pages/auth/Register.tsx`)

Rút gọn còn 5 trường theo đúng thứ tự: Tên cửa hàng, Số điện thoại, Địa chỉ (`<textarea>`), Mật khẩu, Nhập lại mật khẩu. Bỏ input Tên chủ shop và Email. Validate client-side nhập lại mật khẩu khớp bằng `viValidity`/check thủ công trước khi submit (thông báo tiếng Việt), tương tự cách `ChangePassword.tsx` đang làm. `authApi.RegisterPayload` cập nhật type tương ứng (`shop_name`, `phone`, `address`, `password`, `confirm_password`).

### 4.2. State hết hạn dùng chung

Thêm `Tenant.expires_at: string | null` vào type `Tenant` trong `stores/authStore.ts` (đã có field này chảy qua từ `/auth/login`, `/auth/refresh`, `/auth/register`, `/auth/me` vì dùng chung `TenantBrief`).

Hook mới `frontend/src/hooks/useSubscriptionStatus.ts`:

```ts
export function useSubscriptionStatus() {
  const tenant = useAuthStore((s) => s.tenant);
  if (!tenant?.expires_at) return { isExpired: false, daysUntilExpiry: null };
  const diffMs = new Date(tenant.expires_at).getTime() - Date.now();
  return {
    isExpired: diffMs <= 0,
    daysUntilExpiry: Math.ceil(diffMs / 86_400_000),
  };
}
```

### 4.3. Banner cảnh báo sớm

Component `ExpiryWarningBanner` — hiển thị khi `!isExpired && daysUntilExpiry !== null && daysUntilExpiry <= 7`. Nội dung: "⚠️ Gói dịch vụ sắp hết hạn sau {daysUntilExpiry} ngày nữa. Liên hệ để gia hạn." + 2 link Facebook/Zalo (mở tab mới). Có nút tắt (chỉ ẩn cho tab hiện tại, lưu `sessionStorage`, hiện lại khi mở tab mới/đăng nhập lại).

### 4.4. Popup hết hạn (không thể đóng)

Component `ExpiredOverlay` — hiển thị full-screen (`position: fixed; inset: 0; z-index` cao nhất) khi `isExpired === true`. Không có nút đóng/X. Nội dung:
- Tiêu đề: "Gói dịch vụ đã hết hạn"
- Mô tả: "Vui lòng liên hệ để gia hạn và tiếp tục sử dụng dịch vụ."
- Nút "Liên hệ Facebook" → mở tab mới tới `https://www.facebook.com/profile.php?id=61579076336752`
- Nút "Liên hệ Zalo" → mở tab mới tới `https://zalo.me/0392368532`
- Nút "Đăng xuất" → gọi `doLogout()` rồi điều hướng `/login`

### 4.5. Nơi mount

Cả `ExpiryWarningBanner` và `ExpiredOverlay` mount ở `App.tsx`, ngay sau khi `bootstrap()` xong và chỉ khi đã đăng nhập (`tenant !== null`) — đặt là sibling của `<Routes>`, bên trong `<BrowserRouter>`. Lý do đặt ở gốc App thay vì trong `AppLayout`: route `/pos` (POS bán hàng) nằm ngoài `AppLayout` nhưng vẫn cần bị che khi hết hạn.

## 5. Android app

### 5.1. Truyền `expires_at` từ backend

`TenantDto` (`core/network/dto/AuthDtos.kt`) thêm:
```kotlin
@SerialName("expires_at") val expiresAt: String? = null
```
Áp dụng cho cả `LoginResponseDto.tenant` và `TokenRefreshDto.tenant` (cả 2 endpoint `/auth/mobile/login` và `/auth/mobile/refresh` đều trả `TenantBrief` nên tự động có field này).

### 5.2. `CurrentUser` mang theo hạn dùng

`CurrentUser` thêm `val expiresAt: Instant?`. Parse từ ISO string sang `Instant` khi map DTO → domain.

Cập nhật 2 nơi tạo/refresh `CurrentUser`:
- `AuthRepository.login()` — set `expiresAt` khi đăng nhập (đã có sẵn logic set `CurrentUser`, chỉ thêm field).
- `NetworkModule.refreshCallerProvider()` — hiện tại refresh chỉ lấy `accessToken`/`refreshToken` từ `TokenRefreshDto`, bỏ qua `tenant`. Sửa để sau khi refresh thành công, dựng lại `CurrentUser` từ `dto.user`/`dto.tenant` rồi gọi `sessionManager.set(...)` + `tokenStore.saveUser(...)`. Vì access token sống 60 phút và tự refresh khi hết hạn trong lúc dùng app, `expiresAt` được đồng bộ lại định kỳ mà **không cần thêm timer hay endpoint polling riêng**. Cold-start dùng lại giá trị cache trong `TokenStore` (đủ chính xác ở cấp độ tháng).

### 5.3. `SessionManager`

Thêm computed:
```kotlin
val isExpired: StateFlow<Boolean> = current.map { user ->
    user?.expiresAt != null && user.expiresAt <= Clock.System.now()
}.stateIn(...)
```

### 5.4. Overlay chặn

Composable mới `core/ui/ExpiredOverlay.kt`:
- Full-screen, vẽ đè lên trên cùng.
- `BackHandler(enabled = true) {}` — nuốt nút Back cứng, không cho thoát overlay.
- Nội dung tương tự web: tiêu đề, mô tả, nút Facebook/Zalo (`Intent(Intent.ACTION_VIEW, Uri.parse(...))`), nút "Đăng xuất" (gọi `AuthRepository.logout()`, sau đó `sessionManager.current` về `null` nên overlay tự ẩn và điều hướng Login qua `AppNav` như flow logout thông thường hiện có).

### 5.5. Nơi mount

Trong `MainActivity`, thêm `ExpiredOverlay` là 1 phần tử cạnh `AppNav` trong `Box` hiện có, hiển thị điều kiện `sessionManager.current != null && sessionManager.isExpired.collectAsState().value`.

## 6. Error handling & edge cases

- Đăng ký với `password != confirm_password` → lỗi 422 tiếng Việt "Xác nhận mật khẩu không khớp" (validate ở Pydantic field_validator, đồng thời chặn sớm ở client).
- `tenant.expires_at = NULL` (tài khoản admin set tay không giới hạn) → không hiện banner, không hiện popup.
- Gia hạn khi tenant chưa từng hết hạn (đang dùng bình thường) → cộng dồn thêm vào `expires_at` hiện tại, không mất thời gian còn lại.
- Gia hạn khi tenant đã hết hạn từ lâu → tính từ thời điểm gia hạn (hôm nay), không cộng dồn từ quá khứ.
- Nhiều user (OWNER + nhiều CASHIER) cùng 1 tenant hết hạn → tất cả đều thấy popup như nhau (tenant-level, không phải user-level).
- CASHIER không có quyền gia hạn hay thấy nút gì khác ngoài Facebook/Zalo/Đăng xuất — giống hệt OWNER trong popup này (không phân quyền ở đây).

## 7. Testing

- Backend: test `register` thiếu `confirm_password` khớp → 422; test `expires_at` được set đúng `created_at + 6 tháng`; test `TenantBrief` trả `expires_at` qua `/auth/me`, `/login`, `/register`, mobile `/refresh`.
- Backend: test script `extend_tenant.py` — cộng dồn đúng khi còn hạn, tính từ hôm nay khi đã hết hạn, ghi đúng 1 dòng `audit_logs`.
- Frontend: test `useSubscriptionStatus` với các mốc thời gian (còn hạn dài, còn ≤7 ngày, đã hết hạn, `expires_at = null`).
- Frontend: test `ExpiredOverlay` không có phần tử nút đóng/X, hiện đúng 2 link Facebook/Zalo, nút đăng xuất gọi đúng action.
- Frontend: test `Register.tsx` chỉ còn đúng 5 field, validate mật khẩu không khớp hiện lỗi tiếng Việt trước khi gọi API.
- Android: test `SessionManager.isExpired` true/false theo `expiresAt`; test overlay swallow back-press (không điều hướng ra ngoài); test refresh flow cập nhật `expiresAt` mới vào `CurrentUser`.
