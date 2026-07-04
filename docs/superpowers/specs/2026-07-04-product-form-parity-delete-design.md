# Product form parity (app ↔ web) + delete product

**Ngày:** 2026-07-04
**Trạng thái:** Đã duyệt, chờ viết plan

## Bối cảnh

Màn "Thêm sản phẩm" trên app Android đang thiếu nhiều field so với web (nhóm hàng, tồn tối thiểu, trạng thái), không bắt buộc nhập đơn vị/giá nhập/giá bán (chỉ cần tên là lưu được), và không có màn Sửa SP. Cả web và app đều chưa có nút xóa sản phẩm lộ rõ ràng cho người dùng — thực ra web đã có (nút "Ngừng bán" ở trang chi tiết gọi API soft-delete), nhưng Android hoàn toàn chưa có ở bất kỳ layer nào (DTO, API, ViewModel, UI).

Rà soát code phát hiện thêm 1 lỗ hổng: endpoint `DELETE /api/v1/products/{id}` không giới hạn role, trái với bảng phân quyền trong CLAUDE.md (xóa SP: OWNER only).

## Quyết định thiết kế đã chốt

1. **Xóa vs Ngừng bán**: giữ nguyên hành vi hiện tại — nút xóa thực chất là soft-delete (ẩn hẳn khỏi mọi danh sách, không phục hồi). Không tách thành 2 khái niệm riêng (không thêm khái niệm "tạm ngừng bán, vẫn hiện trong DS quản lý").
2. **Bắt buộc giá vốn khi tạo SP mới**: bắt buộc với OWNER, giữ optional với Cashier — vì field giá vốn vốn chỉ hiển thị cho OWNER theo permission hiện tại (Cashier không thấy field nên không thể bắt buộc).
3. **Scope Android**: làm luôn màn Sửa SP (ngoài Thêm mới + Xóa), vì nếu không có màn Sửa thì các field mới (nhóm hàng, tồn tối thiểu, trạng thái) không thể chỉnh lại sau khi tạo trên app.

## Phần 1 — Backend

- Thêm `dependencies=[Depends(require_role("OWNER"))]` vào route `DELETE /api/v1/products/{product_id}` (`backend/modules/product/router.py`) — hiện route này không giới hạn role, Cashier gọi thẳng API vẫn xóa được SP, trái bảng phân quyền CLAUDE.md. Áp dụng đúng pattern đã dùng cho `create_unit`/`update_unit`/`delete_unit`.
- Không đổi schema `ProductCreateRequest`/`ProductUpdateRequest` — các field `unit`/`cost_price`/`sale_price` vẫn optional ở tầng API (có default). Validate "bắt buộc nhập đủ" chỉ áp ở tầng client (web + Android), để không phá các caller khác gọi thẳng API (import Excel sau này, v.v).

## Phần 2 — Web (`frontend/src/pages/products/ProductForm.tsx`)

- Thêm `required` + `viValidity` message tiếng Việt cho input "Đơn vị" (hiện chưa bắt buộc).
- Thêm `required` cho input "Giá vốn" — chỉ áp dụng trong nhánh `isOwner` (field này vốn đã ẩn với Cashier).
- Giữ nguyên nút "Ngừng bán" ở `ProductDetail.tsx` (không đổi label, không đổi hành vi) theo quyết định #1.

## Phần 3 — Android: Thêm SP + Sửa SP

### 3.1 Field bổ sung cho màn Thêm SP (`AddProductScreen.kt`)

- **Nhóm hàng**: nút chọn mở `DropdownMenu` (Material3, cùng pattern đã dùng ở `HubScreen.kt` cho menu Cài đặt), danh sách lấy từ `CategoryRepository.tree()` có sẵn, flatten + thụt lề hiển thị con (giống hàm `flattenCategories` bên web).
- **Tồn tối thiểu**: `AppTextField` kiểu số nguyên, mặc định "0".
- **Trạng thái**: `DropdownMenu` 3 lựa chọn Đang bán/Ngừng bán/Nháp, mặc định "Đang bán".
- `ProductCreateDto` (`core/network/dto/ProductDtos.kt`) thêm field `categoryId: Long? = null` (`@SerialName("category_id")`).

### 3.2 Validate bắt buộc (`AddProductViewModel.submit()` và `EditProductViewModel`)

Bắt buộc (báo lỗi tiếng Việt qua `ErrorDialog` có sẵn, theo đúng field bị thiếu):
- Tên sản phẩm (đã có).
- Đơn vị: không được rỗng.
- Giá bán: phải > 0.
- Giá vốn: bắt buộc **chỉ khi** `SessionManager.isOwner == true` (cùng cờ web dùng). Cashier không thấy field này trong form → không bắt buộc, gửi mặc định "0".

### 3.3 Màn Sửa SP (mới)

Chưa tồn tại trên app hiện tại (chỉ có Thêm mới + Chi tiết chỉ đọc). Thiết kế:

- Tách phần field nhập liệu (tên, sku, barcode, đơn vị, giá vốn, giá bán, nhóm hàng, tồn tối thiểu, trạng thái) từ `AddProductScreen.kt` thành 1 composable dùng chung, ví dụ `ProductFormFields(state, callbacks...)`, để cả `AddProductScreen` và `EditProductScreen` (mới) cùng dùng — tránh trùng lặp layout.
- `EditProductScreen.kt` (mới) + `EditProductViewModel.kt` (mới): load SP hiện tại (dùng lại `ProductListRepository.get(id)` như `ProductDetailViewModel` đang làm), fill vào form, validate giống mục 3.2, submit gọi `ProductRepository.update(id, dto)` (API mới, xem 3.4), thành công thì quay lại màn Chi tiết.
- `ProductDetailScreen.kt`: thêm nút "Sửa" (icon bút) trên `AppHeader`, hiện với **mọi role** (theo bảng phân quyền "Tạo/sửa SP: OWNER + CASHIER"), điều hướng sang `EditProductScreen`.
- Route mới `Routes.PRODUCT_EDIT` (nhận `productId`), wire trong `HomeNavHost.kt`.

### 3.4 DTO / API / Repository mới

- `ProductBriefDto` bổ sung field còn thiếu để phục vụ prefill form Sửa: `categoryId: Long? = null` (`category_id`), `minStock: Int = 0` (`min_stock`), `description: String? = null`.
- `ProductUpdateDto` (mới, mirror `ProductUpdateRequest` bên backend) — tất cả field nullable/optional.
- `ProductApi.kt` thêm:
  - `@PUT("products/{id}") suspend fun update(@Path("id") id: Long, @Body body: ProductUpdateDto): ProductBriefDto`
  - `@DELETE("products/{id}") suspend fun delete(@Path("id") id: Long)` (không cần parse response body, giống `CategoryApi.delete`).
- `ProductRepository.kt` thêm `update(id, dto): ApiResult<ProductBriefDto>` và `delete(id): ApiResult<Unit>`, theo đúng pattern `runCatching {...}.fold(...)` đang dùng.

## Phần 4 — Android: Xóa sản phẩm

- Ở `ProductDetailScreen`: thêm nút "Xóa" — chỉ hiển thị khi `SessionManager.isOwner == true` (khớp fix phân quyền ở Phần 1).
- Bấm nút → mở `ConfirmDialog` (component có sẵn, đã dùng ở `CategoryTreeScreen`) với nội dung cảnh báo rõ ràng: xóa sẽ ẩn hẳn SP khỏi hệ thống, không thể khôi phục.
- Xác nhận → gọi `ProductRepository.delete(id)` → thành công thì quay về màn danh sách SP; lỗi thì hiện `ErrorDialog` có sẵn với message tiếng Việt từ backend.

## Phần 5 — Testing

- **Backend** (`tests/test_product.py`): thêm `test_delete_product_requires_owner` — Cashier gọi `DELETE /products/{id}` → 403 (dùng fixture `registered_cashier` có sẵn, theo pattern trong `tests/test_product_units.py`).
- **Android**: thêm/cập nhật unit test cho `AddProductViewModel.submit()` — case thiếu đơn vị/giá bán → lỗi; OWNER thiếu giá vốn → lỗi; Cashier thiếu giá vốn → vẫn lưu được (mặc định 0). Test tương tự cho `EditProductViewModel`.
- **Web**: không cần test mới — chỉ thêm thuộc tính `required` HTML5, hành vi lưu khi đã điền đủ field không đổi.

## Ngoài phạm vi

- Không tách "trạng thái ACTIVE/INACTIVE" thành hành động riêng biệt với "xóa" — giữ nguyên như quyết định #1.
- Không thêm ràng buộc bắt buộc ở tầng backend schema — chỉ validate ở client.
- Không đổi hành vi/label nút "Ngừng bán" trên web.
