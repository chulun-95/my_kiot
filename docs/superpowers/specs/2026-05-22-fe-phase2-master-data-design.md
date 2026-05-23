# FE Phase 2 — Master Data Design (Products + Categories + Customers + Suppliers)

Status: design (autonomous tick, 2026-05-23)
Spec author: autonomous FE agent
Build context: my_kiot POS — multi-tenant SaaS, FE = React 18 + TS + Tailwind + Zustand + react-router-dom v7 + axios.

## 1. Scope

Implement the four master-data CRUD domains the rest of the build depends on:
- **Products** (CRUD + search + barcode lookup) — feeds POS (Phase 4) and Goods Receipts (Phase 3)
- **Categories** (2-level tree CRUD) — Product.category_id
- **Customers** (CRUD + history + phone lookup) — feeds POS customer pick (Phase 4)
- **Suppliers** (CRUD) — feeds Goods Receipts (Phase 3)

Plus two shared lookup components that Phase 4 will reuse without modification:
- **ProductPicker** — input → autocomplete + barcode lookup
- **CustomerQuickSearch** — phone → single-customer lookup with "create new" fallback

## 2. Routes (react-router v7, nested under `<AppLayout>`)

| Path | Component | Notes |
|------|-----------|-------|
| `/products` | `ProductList` | list + search + paginate |
| `/products/new` | `ProductForm` (mode=create) | shared form |
| `/products/:id/edit` | `ProductForm` (mode=edit) | loads then edits |
| `/products/:id` | `ProductDetail` | read-only detail; links to edit |
| `/categories` | `CategoryTree` | tree view, inline CRUD (modal) |
| `/customers` | `CustomerList` | list + search + paginate |
| `/customers/new` | `CustomerForm` (mode=create) | |
| `/customers/:id` | `CustomerDetail` | profile + purchase history tab |
| `/suppliers` | `SupplierList` | list + search + create-from-list |
| `/suppliers/new` | `SupplierForm` (mode=create) | |
| `/suppliers/:id/edit` | `SupplierForm` (mode=edit) | |

`CustomerForm` edit-mode is reached via the in-place "Edit" toggle inside `CustomerDetail` (no separate `/customers/:id/edit` route — keeps the URL stable while editing).

## 3. Components

### `src/api/product.ts`
Thin wrappers over `apiClient` exposing:
- `listProducts(params)` → `ProductListResponse`
- `getProduct(id)` → `ProductResponse`
- `createProduct(payload)` → `ProductResponse`
- `updateProduct(id, payload)` → `ProductResponse`
- `deleteProduct(id)` → `MessageResponse`
- `searchProducts(q, limit?)` → `ProductSearchResponse` (brief items)
- `getProductByBarcode(code)` → `ProductBriefResponse`

Exports types `ProductResponse`, `ProductBrief`, `ProductCreatePayload`, `ProductUpdatePayload`, `ProductListResponse`, `Pagination`.

### `src/api/category.ts`
- `listCategories()` → `CategoryTreeResponse` (`{ items: CategoryNode[] }`)
- `createCategory(payload)` → `CategoryResponse`
- `updateCategory(id, payload)` → `CategoryResponse`
- `deleteCategory(id)` → `MessageResponse`

### `src/api/customer.ts`
- `listCustomers(params)` → `CustomerListResponse`
- `getCustomer(id)` → `CustomerDetailResponse` (`{ customer, recent_orders }`)
- `createCustomer(payload)` → `CustomerResponse`
- `updateCustomer(id, payload)` → `CustomerResponse`
- `deleteCustomer(id)` → `MessageResponse`
- `getCustomerByPhone(phone)` → `CustomerResponse` (404 if not found — caller catches)

### `src/api/supplier.ts`
- `listSuppliers(params)` → `SupplierListResponse`
- `getSupplier(id)` → `SupplierResponse`
- `createSupplier(payload)` → `SupplierResponse`
- `updateSupplier(id, payload)` → `SupplierResponse`
- `deleteSupplier(id)` → `MessageResponse`

### `src/pages/products/ProductList.tsx`
Server-paged table. Columns: SKU, Tên, Nhóm, Đơn vị, Giá bán, Giá vốn (if available in response), Tồn min, Trạng thái, Hành động (Xem / Sửa / Ngừng bán).
Filters: search input (300ms debounce), category dropdown (loads tree from `/categories`), status filter (ACTIVE / INACTIVE / DRAFT / Tất cả).
"+ Thêm sản phẩm" button → `navigate('/products/new')`.

### `src/pages/products/ProductForm.tsx`
Single form used for create + edit (mode prop derived from `useParams().id`). Fields: name, sku (optional — backend auto-generates), barcode, category_id (select from tree), unit, cost_price, sale_price, min_stock, image_url, status, allow_negative.
On submit → POST or PUT; on success navigate to `/products/:id`. Validation: name required, sale_price >= 0, cost_price >= 0. Surfaces `DUPLICATE_SKU` / `DUPLICATE_BARCODE` errors as field-level messages.

### `src/pages/products/ProductDetail.tsx`
Read-only display of all product fields (formatted prices in VND), with Edit + Soft-delete buttons (latter Owner-only via `RoleGate`).

### `src/pages/categories/CategoryTree.tsx`
Flat-list of parents, each expandable to children (depth=2 enforced by backend; FE prevents the "Add subcategory" action on already-depth-2 nodes). Inline modal `CategoryForm` for create/edit. Delete confirms; surfaces backend's "category has products" 409 message via `toFriendlyMessage`. Drag-sort is **explicitly deferred** to Phase 6 polish — we expose `sort_order` as a numeric input in the create/edit modal instead (low-tech but adequate).

### `src/pages/customers/CustomerList.tsx`
Server-paged table. Columns: Tên, SĐT, Email, Tổng chi tiêu (formatVND), Số đơn, Lần mua cuối (formatDate). Search input filters by name/phone (backend handles both). "+ Thêm khách hàng" navigates to `/customers/new`.

### `src/pages/customers/CustomerForm.tsx`
Fields: name (required), phone, email, address, note. Phone format hint shown (VN regex `^0[3|5|7|8|9]\d{8}$`) but not strictly enforced FE-side (backend rejects bad formats; we surface error).

### `src/pages/customers/CustomerDetail.tsx`
Two tabs: "Thông tin" (read-only fields + Edit toggle that swaps to inline form) and "Lịch sử mua" (recent_orders table: code, completed_at, total, status). Soft-delete button (Owner only via `RoleGate`).

### `src/pages/suppliers/SupplierList.tsx`
Same pattern as `CustomerList`. Columns: Tên, SĐT, Email, Mã số thuế, Công nợ (formatVND). "+ Thêm nhà cung cấp" → `/suppliers/new`. Edit via row action → `/suppliers/:id/edit`.

### `src/pages/suppliers/SupplierForm.tsx`
Fields: name (required), phone, email, address, tax_code, note. Same create/edit mode pattern as ProductForm.

### `src/components/ProductPicker.tsx` (shared, used Phase 4)
Props: `onPick: (product: ProductBrief) => void`, `autoFocus?: boolean`.
Behavior:
1. Input has `ref` for keyboard focus. As user types: 250ms debounce, then `searchProducts(q, 8)`; show dropdown of brief results.
2. Keyboard barcode scanner emits Enter at end. On Enter:
   - if the input value is purely digits and length >= 6 → call `getProductByBarcode(value)`; on success → `onPick` + clear input + refocus.
   - else if dropdown has a highlighted item → pick that one.
3. Arrow keys navigate dropdown; Esc clears.

### `src/components/CustomerQuickSearch.tsx` (shared, used Phase 4)
Props: `onPick: (customer: CustomerResponse | null) => void`, `allowGuest?: boolean` (default true), `initial?: string` (prefill phone).
Behavior: tel input. On blur or Enter, if value looks like a phone (digits, length 9-11), call `getCustomerByPhone`; on 404, render "Không tìm thấy — Thêm khách mới" button that opens the inline mini form (name + phone) → POST → `onPick`. Owner click "Khách vãng lai" calls `onPick(null)`.

## 4. State

No new Zustand stores — list pages own `useState` + `useEffect` like `StaffList`. Reason: list state is page-local and doesn't need to be shared. The shared lookup components (`ProductPicker`, `CustomerQuickSearch`) emit results via callbacks; the consumer page holds the picked entity in local state.

`authStore` already exposes `user.role` for `RoleGate`-style guards.

## 5. API mapping table

| HTTP method | Endpoint | Caller (file / fn) | Request shape | Response handling |
|---|---|---|---|---|
| GET | `/products?page&limit&search&category_id&status` | `productApi.listProducts` (`ProductList`) | query params | `setState(items, pagination)` |
| GET | `/products/{id}` | `productApi.getProduct` (`ProductDetail`, `ProductForm` edit) | path | render fields |
| POST | `/products` | `productApi.createProduct` (`ProductForm`) | body = ProductCreateRequest | navigate `/products/{id}` |
| PUT | `/products/{id}` | `productApi.updateProduct` (`ProductForm`) | body = ProductUpdateRequest | navigate `/products/{id}` |
| DELETE | `/products/{id}` | `productApi.deleteProduct` (`ProductDetail`) | path | re-route to `/products` |
| GET | `/products/search?q&limit` | `productApi.searchProducts` (`ProductPicker`) | query | dropdown items |
| GET | `/products/barcode/{code}` | `productApi.getProductByBarcode` (`ProductPicker`) | path | onPick |
| GET | `/categories` | `categoryApi.listCategories` (`CategoryTree`, `ProductForm` for dropdown) | — | render tree |
| POST | `/categories` | `categoryApi.createCategory` (`CategoryTree`) | body | refresh tree |
| PUT | `/categories/{id}` | `categoryApi.updateCategory` (`CategoryTree`) | body | refresh tree |
| DELETE | `/categories/{id}` | `categoryApi.deleteCategory` (`CategoryTree`) | path | refresh tree, surface 409 |
| GET | `/customers?page&limit&search` | `customerApi.listCustomers` (`CustomerList`) | query | render rows |
| GET | `/customers/{id}` | `customerApi.getCustomer` (`CustomerDetail`) | path | render tabs |
| POST | `/customers` | `customerApi.createCustomer` (`CustomerForm`, `CustomerQuickSearch` inline create) | body | navigate or onPick |
| PUT | `/customers/{id}` | `customerApi.updateCustomer` (`CustomerDetail` edit) | body | reload detail |
| DELETE | `/customers/{id}` | `customerApi.deleteCustomer` (`CustomerDetail`) | path | navigate `/customers` |
| GET | `/customers/phone/{phone}` | `customerApi.getCustomerByPhone` (`CustomerQuickSearch`) | path | onPick or fallback |
| GET | `/suppliers?page&limit&search` | `supplierApi.listSuppliers` (`SupplierList`) | query | render rows |
| GET | `/suppliers/{id}` | `supplierApi.getSupplier` (`SupplierForm` edit) | path | prefill |
| POST | `/suppliers` | `supplierApi.createSupplier` (`SupplierForm`) | body | navigate `/suppliers` |
| PUT | `/suppliers/{id}` | `supplierApi.updateSupplier` (`SupplierForm`) | body | navigate `/suppliers` |
| DELETE | `/suppliers/{id}` | `supplierApi.deleteSupplier` (`SupplierList`) | path | reload |

## 6. Edge cases & error handling

- **Soft-delete (`deleted_at`):** backend returns 200 with message on DELETE; row disappears from subsequent lists (backend filters `deleted_at IS NULL`). UI shows a confirm dialog and removes the row optimistically? No — keep simple: refetch list after delete.
- **SKU / barcode uniqueness (409):** map `DUPLICATE_SKU` / `DUPLICATE_BARCODE` via `toFriendlyMessage`; surface beside the offending field if the form can determine which one (default to top-of-form).
- **Cost visibility:** `ProductResponse.cost_price` arrives as `null` for CASHIER when `show_cost_to_cashier=false`. UI renders "—" in that case; the form's cost_price input is hidden for CASHIER (we read role from `authStore`). Mutation is allowed regardless (backend rejects with FORBIDDEN if the role can't actually write).
- **Category depth 2:** when calling `createCategory` with `parent_id`, FE verifies the parent has `depth === 1`; the "Add subcategory" button is disabled on depth-2 nodes. Backend is the source of truth — FE just avoids obvious UX dead-ends.
- **Customer phone format:** `^0[3|5|7|8|9]\d{8}$` regex displayed as helper text; not strictly enforced FE-side (backend validates).
- **Customer 404 on phone lookup:** `CustomerQuickSearch` catches axios 404 and switches to "create new" mode instead of bubbling an error.
- **Pagination edge:** if `total_pages = 0` (empty list), show "Chưa có dữ liệu" and disable both pagination buttons.

## 7. Test plan

| Test file | What it asserts |
|---|---|
| `api/__tests__/product.test.ts` | list/get/create/update/delete/search/barcode wrappers fire correct verbs/paths against MSW |
| `api/__tests__/category.test.ts` | tree/create/update/delete wrappers |
| `api/__tests__/customer.test.ts` | list/get (incl. recent_orders)/create/update/delete/by-phone wrappers, 404 from by-phone propagates |
| `api/__tests__/supplier.test.ts` | list/get/create/update/delete wrappers |
| `pages/products/__tests__/ProductList.test.tsx` | renders rows, search input fires GET with `search=` param, empty-state |
| `pages/products/__tests__/ProductForm.test.tsx` | create submits POST with form body, edit prefills then PUTs, duplicate-SKU 409 surfaces friendly error |
| `pages/categories/__tests__/CategoryTree.test.tsx` | 2-level tree renders, depth-2 node disables "Add subcategory" button |
| `pages/customers/__tests__/CustomerList.test.tsx` | renders rows, search fires GET, empty-state |
| `pages/suppliers/__tests__/SupplierList.test.tsx` | renders rows, create-from-modal not used (we use route) — instead verify navigate to `/suppliers/new` button is present |
| `components/__tests__/ProductPicker.test.tsx` | typing triggers debounced search, Enter on numeric barcode triggers barcode-lookup endpoint |
| `components/__tests__/CustomerQuickSearch.test.tsx` | phone lookup happy path; 404 swap to create-new form |

Total new test files: 11. Existing 36 tests must still pass.

## 8. Out of scope (deferred)

- Excel import for products (`POST /products/import`) — backlog #3, not exposed.
- Drag-and-drop category reordering — Phase 6 polish.
- Product image upload UI (Cloudflare R2 presigned URL flow) — Phase 6.
- Editing customer/supplier within a modal vs page route — we picked routes; modals can be added later without API churn.
