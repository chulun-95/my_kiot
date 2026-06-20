# Spec: Android SP-1 — Catalog & Kho vận hành + Foundation phân quyền

Ngày: 2026-06-20 · Branch: fix/return-debt-business-logic

## Bối cảnh & mục tiêu

App Android (Jetpack Compose, MVVM, Hilt, Material 3) đang thiếu một số chức năng so với
web. Mục tiêu tổng: **app đủ chức năng để không cần web**, dùng cho **cả OWNER và CASHIER**
với phân quyền đúng bảng trong `CLAUDE.md`.

Toàn bộ công việc chia thành 4 sub-project (mỗi cái spec→plan→implement riêng):

- **SP-1 (spec này):** Nhà cung cấp, Nhóm hàng, Lịch sử phiếu nhập, Tồn kho + tab "Sắp hết",
  + **Foundation:** session/role-gating và component `ErrorDialog` dùng chung.
- SP-2: Sổ quỹ thu/chi, Điều chỉnh tồn kho (kiểm kê).
- SP-3: Dashboard + 7 báo cáo.
- SP-4: Quản lý nhân viên, Đăng ký shop, hoàn thiện role-gating.

**Ràng buộc:** mọi text hiển thị **tiếng Việt** (`strings.xml` + `ResProvider`); lỗi hiển thị
bằng **dialog** (không toast/snackbar — xem Foundation §3). Tất cả màn theo pattern MVVM sẵn có:
`Screen` + `UiState` + `@HiltViewModel` + `Repository` + Retrofit `Api` + DTO, dùng
`ApiResult`/`ErrorMapper`, `collectAsStateWithLifecycle`, đăng ký API trong `NetworkModule`.

**Backend:** mọi endpoint cần thiết đã có sẵn — không sửa backend trong SP-1.
- Categories: `GET /categories` (cây), `POST`, `PUT /{id}`, `DELETE /{id}`
- Suppliers: `GET /suppliers`, `GET /{id}`, `POST`, `PUT /{id}`, `DELETE /{id}`
- Goods receipts: `GET /goods-receipts` (list), `GET /{id}`
- Inventory: `GET /inventory`, `GET /inventory/low-stock`

---

## Foundation

### 1. SessionManager + persist role

Hiện `CurrentUser.role` chỉ trả về lúc login, **không persist** → sau cold-start auto-login
(qua `tokenStore.hasSession()`) Hub không biết role. Phương án **A — Persist + lazy refresh**:

- **`core/auth/SessionManager.kt` (`@Singleton`):** giữ `StateFlow<CurrentUser?>`, là nguồn
  sự thật về user/role cho toàn app. API: `current: StateFlow<CurrentUser?>`, `set(user)`, `clear()`,
  `restore()` (đọc từ store).
- **`EncryptedTokenStore`/`TokenStore`:** thêm lưu/đọc `CurrentUser` (keys: `user_id`, `role`,
  `full_name`, `tenant_id`, `tenant_name`). `clear()` xóa luôn các key này.
- **`AuthRepository.login()` thành công:** ngoài lưu token → lưu `CurrentUser` vào store +
  `sessionManager.set(user)`.
- **Cold start** (`MainActivity`/`MyKiotApp`): nếu `hasSession()` → `sessionManager.restore()`
  để Hub render tức thì, không chờ mạng (hoạt động offline).
- **Logout / bị `TokenAuthenticator` buộc đăng xuất:** `tokenStore.clear()` + `sessionManager.clear()`
  → điều hướng về Login.

### 2. Role-gating ở Hub

- `HubScreen` lấy `role` qua `HubViewModel` (inject `SessionManager`).
- Enforce `HubItem.ownerOnly` (field đã có sẵn): lọc bỏ thẻ `ownerOnly` khi `role != "OWNER"`.
  Nhóm rỗng sau lọc → ẩn cả `SectionHeader`.
- SP-1 chưa thêm thẻ `ownerOnly` mới (NCC/Nhóm hàng/Lịch sử nhập/Tồn kho đều CASHIER được dùng),
  nhưng hạ tầng gating sẵn sàng cho SP-2/3/4.

### 3. ErrorDialog — component lỗi dùng chung

Quy ước toàn app: **lỗi hiển thị bằng dialog, không toast/snackbar.**

- **`core/ui/ErrorDialog.kt`** (mirror `ConfirmDialog.kt`): input `ApiError` (`code`, `message`,
  `httpStatus`) + `onDismiss`. Nội dung: **icon theo loại lỗi** + `message` (tiếng Việt) + 1 button **"Đóng"**.
- Map icon: mạng/timeout (không httpStatus) → `CloudOff`; 401/403 → `Lock`; 400/409/422 → `ErrorOutline`;
  404 → `SearchOff`; 500/khác → `ErrorOutline` (tint `error`).
- **Quy ước:** mỗi `UiState` mang `error: ApiError?`; Screen render `ErrorDialog` khi non-null,
  `onDismiss` → VM clear `error`. Toast cho **thành công** ("Đã lưu") được giữ; quy ước này chỉ cho **lỗi**.
- **Migrate ~10 màn cũ** đang dùng Snackbar/Toast cho lỗi sang `ErrorDialog`:
  `ChangePasswordScreen`, `AddCustomerScreen`, `InventoryScreen`, `InvoiceListScreen`,
  `ReturnFormScreen`, `ReturnsScreen`, `PosScreen`, `AddProductScreen`, `ProductListScreen`,
  `GoodsReceiptDetailScreen`.

### 4. Chính sách token khi đổi role (ghi nhận — implement ở SP-4)

Khi OWNER đổi role / khóa nhân viên (màn Quản lý NV — SP-4) → backend revoke toàn bộ refresh
token của user đó (`revoked_at`, cả `family_id`). App: lần refresh kế tiếp (≤60 phút, khi access
token hết hạn) thất bại → `TokenAuthenticator` đẩy về Login → đăng nhập lại lấy role mới. Không
rủi ro leo thang quyền vì backend luôn enforce `require_role` từng request. SP-1 chỉ cần xử lý
đúng luồng "bị buộc logout" (đã có ở Foundation §1).

---

## Tính năng

### F1 — Nhà cung cấp (NCC) `feature/supplier`

Tận dụng `AddSupplierViewModel`/`AddSupplierScreen`/`SupplierRepository` đã có (hiện chưa nối Hub).

- **`SupplierApi`** thêm: `getById(id)` (GET `/suppliers/{id}`), `update(id, body)` (PUT `/suppliers/{id}`).
- **DTO:** supplier DTOs hiện nằm trong `dto/InventoryDtos.kt` (`SupplierDto`, `SupplierCreateDto`,
  `SupplierListDto`). Thêm `SupplierUpdateDto` (hoặc tái dùng `SupplierCreateDto`) và đảm bảo
  `SupplierDto` có `total_debt`. (Tùy chọn: tách ra `dto/SupplierDtos.kt` cho gọn — không bắt buộc.)
- **`SupplierRepository`** thêm `list(search)`, `getById`, `update`.
- **Mới:** `SupplierListScreen` + `SupplierListViewModel` + `SupplierListUiState`: ô tìm kiếm
  (search debounce, `list(search=)`), mỗi dòng hiện **tên / SĐT / công nợ** (`total_debt`, format
  bằng `Money`), nút "+" thêm. Empty-state "Chưa có nhà cung cấp".
- **Sửa:** `AddSupplierScreen` nhận `supplierId: Long?` → có id thì prefill (gọi `getById`) +
  submit `update`; không id thì `create`. Tiêu đề đổi theo chế độ.
- **Routes:** `SUPPLIERS`, `SUPPLIER_ADD`, `SUPPLIER_EDIT = "supplier_edit/{id}"` + `supplierEdit(id)`.

### F2 — Nhóm hàng (Categories) `feature/category` (mới)

- **`CategoryApi`** (mới): `tree()` (GET `/categories`), `create(body)`, `update(id, body)`,
  `delete(id)`.
- **DTO** `dto/CategoryDtos.kt`: `CategoryDto` (id, name, parentId, depth, children),
  `CategoryTreeDto`, `CategoryCreateDto` (name, parentId?).
- **`CategoryRepository`** (mới).
- **`CategoryTreeScreen` + `CategoryViewModel` + `CategoryUiState`:** hiển thị **cây 2 cấp**
  (cha → con, expand/collapse). Hành động: thêm cấp 1, thêm cấp 2 (chọn cha), sửa tên, xóa.
  Form thêm/sửa bằng `AlertDialog` + `AppTextField`. Xóa nhóm có SP → backend trả lỗi →
  `ErrorDialog` (message tiếng Việt). Empty-state "Chưa có nhóm hàng".
- **Routes:** `CATEGORIES`.

### F3 — Lịch sử phiếu nhập `feature/receipt`

- **`InventoryApi`** thêm: `listReceipts(page, limit, ...)` (GET `/goods-receipts`). DTO
  `GoodsReceiptListDto` + `GoodsReceiptBriefDto` (mã, NCC, tổng, trạng thái, ngày) trong
  `dto/InventoryDtos.kt`.
- **`ReceiptRepository`** thêm `listReceipts(...)`.
- **`GoodsReceiptListScreen` + `GoodsReceiptListViewModel` + UiState:** danh sách phân trang
  (dùng `PagedLazyColumn` sẵn có), mỗi dòng: mã phiếu / NCC / tổng tiền / chip trạng thái / ngày.
  Tap dòng → `GoodsReceiptDetailScreen` (đã có). Empty-state "Chưa có phiếu nhập".
- **Routes:** `RECEIPT_HISTORY`. (Thẻ Hub riêng.)

### F4 — Tồn kho + tab "Sắp hết" `feature/inventory`

- API đã có (`inventory()`, `lowStock()`).
- **Sửa `InventoryScreen` + `InventoryViewModel` + `InventoryUiState`:** thêm `TabRow` 2 tab —
  **"Tất cả"** (paging + search như hiện tại) / **"Sắp hết"** (gọi `lowStock()`, danh sách riêng).
  UiState thêm `selectedTab` + `lowStockItems` + `lowStockLoading`. Giữ `MovementsDialog` (kardex).
  Không thêm route mới.

---

## Thay đổi Hub (IA)

`HubScreen.hubGroups`:
- **Nhóm Kho:** Nhập hàng, Tồn kho, **Lịch sử nhập** (mới — icon `History`), Đổi/trả hàng.
- **Nhóm Danh mục:** Sản phẩm, **Nhóm hàng** (mới — icon `Category`), **Nhà cung cấp**
  (mới — icon `LocalShipping`), Khách hàng.
- Các nhóm khác giữ nguyên. Thêm chuỗi i18n cho 3 thẻ mới trong `strings.xml`.
- Wiring: thêm `composable(...)` tương ứng trong `HomeNavHost` (dùng `navigateOnce`/`popOnce` +
  `FeatureScaffold`), import màn mới.

---

## Kiểm thử

- **Unit test ViewModel** (repo fake trả `ApiResult`) cho mỗi VM mới/đổi:
  - `SupplierListViewModel`: loading/success/error, search debounce.
  - `AddSupplierViewModel`: chế độ create vs edit (prefill + update).
  - `CategoryViewModel`: tải cây, thêm/sửa/xóa, lỗi xóa-có-SP → `error` được set.
  - `GoodsReceiptListViewModel`: paging, empty, error.
  - `InventoryViewModel`: chuyển tab, tải low-stock.
  - `SessionManager`: persist → restore role; `clear()` khi logout.
- **Build xanh:** `./gradlew :app:assembleDebug` + `:app:testDebugUnitTest` trước khi xong.
- Không thêm instrumentation/UI test (giữ scope MVP).

## Phạm vi — không làm trong SP-1

- Không màn chi tiết NCC (công nợ + lịch sử nhập theo NCC) — chỉ List + Form (ngang web).
- Không sửa backend/web.
- Sổ quỹ, điều chỉnh tồn, báo cáo, quản lý NV → SP-2/3/4.
- Backend revoke-token-on-role-change → implement ở SP-4 (SP-1 chỉ ghi nhận chính sách).
