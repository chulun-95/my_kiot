# FE Phase 2 — Master Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement React UI + API wrappers for Products, Categories, Customers, Suppliers + two shared lookup components (`ProductPicker`, `CustomerQuickSearch`), wired into the existing `AppLayout` router.

**Architecture:** Each domain gets a thin axios wrapper module in `src/api/`, plus list/form/detail pages under `src/pages/<domain>/`. Pages own local `useState`/`useEffect` — no new Zustand stores. Shared lookup components live in `src/components/` for Phase 4 reuse.

**Tech Stack:** React 18, TypeScript, Tailwind (utility classes), react-router-dom v7, axios, Zustand (auth only), Vitest + RTL + MSW.

---

## File Structure

**API wrappers (4 new files):**
- `frontend/src/api/product.ts` — listProducts, getProduct, createProduct, updateProduct, deleteProduct, searchProducts, getProductByBarcode + types
- `frontend/src/api/category.ts` — listCategories, createCategory, updateCategory, deleteCategory + types
- `frontend/src/api/customer.ts` — listCustomers, getCustomer, createCustomer, updateCustomer, deleteCustomer, getCustomerByPhone + types
- `frontend/src/api/supplier.ts` — listSuppliers, getSupplier, createSupplier, updateSupplier, deleteSupplier + types

**Pages (9 new files):**
- `frontend/src/pages/products/ProductList.tsx`
- `frontend/src/pages/products/ProductForm.tsx`
- `frontend/src/pages/products/ProductDetail.tsx`
- `frontend/src/pages/categories/CategoryTree.tsx`
- `frontend/src/pages/customers/CustomerList.tsx`
- `frontend/src/pages/customers/CustomerForm.tsx`
- `frontend/src/pages/customers/CustomerDetail.tsx`
- `frontend/src/pages/suppliers/SupplierList.tsx`
- `frontend/src/pages/suppliers/SupplierForm.tsx`

**Shared components (2 new files):**
- `frontend/src/components/ProductPicker.tsx`
- `frontend/src/components/CustomerQuickSearch.tsx`

**Modified files:**
- `frontend/src/App.tsx` — wire new routes
- `frontend/src/components/AppLayout.tsx` — sidebar nav stays as-is (it already lists Sản phẩm / Nhóm hàng / Khách hàng / Nhà cung cấp)
- `frontend/src/__tests__/mocks/handlers.ts` — extend with products/categories/customers/suppliers handlers

**Test files (11 new):**
- `frontend/src/api/__tests__/product.test.ts`
- `frontend/src/api/__tests__/category.test.ts`
- `frontend/src/api/__tests__/customer.test.ts`
- `frontend/src/api/__tests__/supplier.test.ts`
- `frontend/src/pages/products/__tests__/ProductList.test.tsx`
- `frontend/src/pages/products/__tests__/ProductForm.test.tsx`
- `frontend/src/pages/categories/__tests__/CategoryTree.test.tsx`
- `frontend/src/pages/customers/__tests__/CustomerList.test.tsx`
- `frontend/src/pages/suppliers/__tests__/SupplierList.test.tsx`
- `frontend/src/components/__tests__/ProductPicker.test.tsx`
- `frontend/src/components/__tests__/CustomerQuickSearch.test.tsx`

---

## Task 1: MSW handlers for new endpoints

**Files:**
- Modify: `frontend/src/__tests__/mocks/handlers.ts`

Add handlers for: `*/products`, `*/products/:id`, `*/products/search`, `*/products/barcode/:code`, `*/categories`, `*/categories/:id`, `*/customers`, `*/customers/:id`, `*/customers/phone/:phone`, `*/suppliers`, `*/suppliers/:id`. Return realistic shapes matching `ProductResponse` / `CategoryNode` / `CustomerResponse` / `SupplierResponse`. Append after existing handlers — don't replace.

## Task 2: `src/api/product.ts`

Type definitions: `Pagination`, `ProductResponse`, `ProductBrief`, `ProductCreatePayload`, `ProductUpdatePayload`, `ProductListResponse`, `ProductSearchResponse`, `MessageResponse`.

Exported functions: `listProducts(params)`, `getProduct(id)`, `createProduct(payload)`, `updateProduct(id, payload)`, `deleteProduct(id)`, `searchProducts(q, limit?)`, `getProductByBarcode(code)`. Mirror the staff.ts style (`apiClient.get/post/put/delete<T>`).

## Task 3: `src/api/category.ts`

Types: `CategoryResponse`, `CategoryNode` (recursive), `CategoryTreeResponse`, `CategoryCreatePayload`, `CategoryUpdatePayload`. Functions: `listCategories()`, `createCategory(payload)`, `updateCategory(id, payload)`, `deleteCategory(id)`.

## Task 4: `src/api/customer.ts`

Types: `CustomerResponse`, `CustomerListResponse`, `CustomerOrderHistoryItem`, `CustomerDetailResponse`, `CustomerCreatePayload`, `CustomerUpdatePayload`. Functions: `listCustomers(params)`, `getCustomer(id)`, `createCustomer(payload)`, `updateCustomer(id, payload)`, `deleteCustomer(id)`, `getCustomerByPhone(phone)`.

## Task 5: `src/api/supplier.ts`

Types: `SupplierResponse`, `SupplierListResponse`, `SupplierCreatePayload`, `SupplierUpdatePayload`. Functions: `listSuppliers(params)`, `getSupplier(id)`, `createSupplier(payload)`, `updateSupplier(id, payload)`, `deleteSupplier(id)`.

## Task 6: API wrapper tests

Write 4 test files exercising each wrapper against MSW. Pattern: `await api.fn()` then assert response shape.

## Task 7: `ProductList.tsx`

Page-level component reading `useSearchParams`-driven page + search + category_id + status. Renders table with columns SKU/Tên/Nhóm/Đơn vị/Giá bán/Tồn min/Trạng thái/Hành động. Top bar has search input (300ms debounce), category select (loads from `listCategories`), status select, "+ Thêm" button → `useNavigate()('/products/new')`. Empty state "Chưa có sản phẩm". Pagination at bottom.

## Task 8: `ProductForm.tsx`

Mode derived from `useParams().id`. On create: empty defaults. On edit: load via `getProduct(id)` on mount, prefill fields. Fields: name, sku, barcode, category_id, unit, cost_price, sale_price, min_stock, image_url, status, allow_negative. Submit → POST or PUT; navigate `/products/:id` on success. Surface errors via `toFriendlyMessage`. Hide cost_price field for non-OWNER role.

## Task 9: `ProductDetail.tsx`

Loads via `getProduct(id)`. Displays all fields formatted. Buttons: "Sửa" → `/products/:id/edit`, "Ngừng bán" (Owner only via `RoleGate`) → `deleteProduct(id)` then navigate `/products`.

## Task 10: `CategoryTree.tsx`

Loads tree via `listCategories()`. Renders parents as a flat list; each can be expanded to show its children. Buttons per row: "Sửa", "Xóa", "+ Thêm con" (disabled if depth=2 or if row is itself a child). "+ Thêm nhóm cha" at top. Modal `CategoryForm` (inline component in the same file) for create/edit. Confirm before delete; surface 409 errors.

## Task 11: `CustomerList.tsx`

Pattern identical to `ProductList` but for customers. Columns: Tên/SĐT/Email/Tổng chi tiêu/Số đơn/Lần mua cuối. Search debounced 300ms.

## Task 12: `CustomerForm.tsx`

Single create/edit form (mode prop). Fields: name, phone, email, address, note. Phone helper text mentions VN format. On create → POST → navigate `/customers/:id`. On edit (rendered inside `CustomerDetail` toggle) → PUT → onSaved callback.

## Task 13: `CustomerDetail.tsx`

Loads `getCustomer(id)`. Two tabs:
1. "Thông tin" — read-only or `CustomerForm` (mode=edit) when edit toggle clicked
2. "Lịch sử mua" — list of `recent_orders` (code, completed_at, total, status)

Soft-delete button (Owner only) navigates to `/customers` after success.

## Task 14: `SupplierList.tsx`

Same pattern as `CustomerList`. Columns: Tên/SĐT/Email/Mã số thuế/Công nợ. Row actions: Sửa → `/suppliers/:id/edit`, Xóa with confirm.

## Task 15: `SupplierForm.tsx`

Single create/edit form. Mode derived from `useParams().id` for the route. Fields: name, phone, email, address, tax_code, note.

## Task 16: `ProductPicker.tsx` (shared)

Props: `onPick: (product: ProductBrief) => void`, `autoFocus?: boolean`, `placeholder?: string`.

Logic:
1. Input value state. On change: clear if empty; else debounce 250ms then call `searchProducts(q, 8)` → store results in `items` state, set `highlight = 0`.
2. On Enter:
   - If value is purely digits, length >= 6 → call `getProductByBarcode(value)`. On success → `onPick(brief)` + clear input. On 404 → set inline error "Không tìm thấy mã vạch".
   - Else if `items.length > 0` → `onPick(items[highlight])` + clear.
3. ArrowDown / ArrowUp: move highlight. Esc: clear.

Dropdown shows up to 8 results: name + sku + sale_price (formatVND). Highlighted row has `bg-slate-100`.

## Task 17: `CustomerQuickSearch.tsx` (shared)

Props: `onPick: (customer: CustomerResponse | null) => void`, `allowGuest?: boolean` (default true), `initial?: string`.

UI: tel input + "Khách vãng lai" button (if `allowGuest`).

Logic:
1. On Enter or blur, if value has 9-11 digits → call `getCustomerByPhone(value)`.
2. On 404 → switch to inline "create new" form: name input + Save button → POST `createCustomer({name, phone: value})` → `onPick(created)`.
3. "Khách vãng lai" → `onPick(null)`.

## Task 18: Wire new routes in `App.tsx`

Replace each `<Placeholder>` route under `/products`, `/categories`, `/customers`, `/suppliers` with real components. Add new nested routes `/products/new`, `/products/:id/edit`, `/products/:id`, `/customers/new`, `/customers/:id`, `/suppliers/new`, `/suppliers/:id/edit`.

## Task 19: Component tests

11 test files (listed in spec §7). Use MemoryRouter when needed. Render → wait for items → assert. Mock window.confirm where deletes are triggered.

## Task 20: Run `tsc --noEmit` and `npm run test -- --run`

Fix any type errors. Capture test pass/fail count. Commit.

---

## Notes

- Field-level error surfacing for forms: keep minimal — show one banner with `toFriendlyMessage(err)`. We don't have a form library; manual `useState` is enough.
- For Decimal fields (cost_price, sale_price, total_spent, total_debt), the backend returns string-or-number JSON. The wrappers type them as `number | string` to be permissive; pages use `formatVND` which handles both.
- We don't add Recharts here — only used in Phase 5.
