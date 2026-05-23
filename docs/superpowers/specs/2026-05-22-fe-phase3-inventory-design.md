# FE Phase 3 — Inventory & Goods Receipts (Design)

Topic: `inventory`
Built on: Phase 0 (scaffolding), Phase 1 (auth/role gates), Phase 2 (Product / Supplier / ProductPicker).

## 1. Scope

Two backend modules in one phase, sharing inventory state:

1. **Goods Receipts** — `goods_receipts` (DRAFT → COMPLETED | CANCELLED). On COMPLETE: cộng tồn, ghi `stock_movements (RECEIPT)`, cập nhật `cost_price` bình quân. On CANCEL: bút toán ngược `CANCEL_RECEIPT`.
2. **Inventory** — list tồn kho hiện tại, low-stock, kardex (stock_movements) cho 1 SP, và OWNER-only stock adjustments (bulk stocktake).

UI in Vietnamese, Tailwind utility-first, no Redis/global stock store (page-owns-state).

## 2. Routes (react-router v6)

| Path | Component | Auth | Role |
|---|---|---|---|
| `/goods-receipts` | `GoodsReceiptList` | Protected | any |
| `/goods-receipts/new` | `GoodsReceiptForm` (create mode) | Protected | any |
| `/goods-receipts/:id` | `GoodsReceiptDetail` | Protected | any (cancel-completed gated inside) |
| `/inventory` | `InventoryList` | Protected | any |
| `/inventory/low-stock` | `LowStock` | Protected | any |
| `/inventory/:productId/movements` | `Kardex` | Protected | any |
| `/inventory/adjustments` | `AdjustmentList` (Owner gate) | Protected | OWNER |
| `/inventory/adjustments/new` | `AdjustmentForm` (Owner gate) | Protected | OWNER |

Sidebar (Vietnamese): adds 3 entries — **Nhập kho**, **Tồn kho**, **Điều chỉnh kho** (Owner-only, behind same role check as Nhân viên).

## 3. API mapping

All endpoints under `/api/v1` (baseURL handled by `src/api/client.ts`).

| Backend endpoint | FE function | Caller |
|---|---|---|
| `GET    /goods-receipts?page&limit&status&supplier_id` | `goodsReceiptApi.list(params)` | `GoodsReceiptList` |
| `GET    /goods-receipts/:id` | `goodsReceiptApi.get(id)` | `GoodsReceiptDetail`, `GoodsReceiptForm` (edit) |
| `POST   /goods-receipts` | `goodsReceiptApi.create(payload)` | `GoodsReceiptForm` (create) |
| `PUT    /goods-receipts/:id` | `goodsReceiptApi.update(id, payload)` | `GoodsReceiptForm` (edit DRAFT) |
| `POST   /goods-receipts/:id/complete` | `goodsReceiptApi.complete(id)` | `GoodsReceiptDetail` Complete button |
| `POST   /goods-receipts/:id/cancel` | `goodsReceiptApi.cancel(id, reason?)` | `GoodsReceiptDetail` Cancel button |
| `GET    /inventory?page&limit&search&only_with_stock` | `inventoryApi.list(params)` | `InventoryList` |
| `GET    /inventory/low-stock` | `inventoryApi.getLowStock()` | `LowStock` |
| `GET    /inventory/:productId/movements?page&limit` | `inventoryApi.getMovements(id, params)` | `Kardex` |
| `POST   /inventory/adjustments` | `inventoryApi.createAdjustment(payload)` | `AdjustmentForm` |
| `GET    /inventory/adjustments?page&limit` | `inventoryApi.listAdjustments(params)` | `AdjustmentList` |

Existing endpoints reused: `GET /suppliers` (for receipt form supplier dropdown), `GET /products/search` (via `ProductPicker`).

## 4. Components

### 4.1 `src/api/goodsReceipt.ts`
Exports types `GoodsReceiptBrief`, `GoodsReceiptResponse`, `GoodsReceiptItemResponse`, `GoodsReceiptItemInput`, `GoodsReceiptCreatePayload`, `GoodsReceiptUpdatePayload`, `GoodsReceiptListResponse`, `Pagination`, and functions `list, get, create, update, complete, cancel`.

### 4.2 `src/api/inventory.ts`
Exports types `InventoryItem`, `InventoryListResponse`, `LowStockItem`, `LowStockResponse`, `StockMovement`, `StockMovementsResponse`, `AdjustmentItemInput`, `AdjustmentResultItem`, `AdjustmentResponse`, `AdjustmentMovement`, `AdjustmentMovementsResponse`, and functions `list, getLowStock, getMovements, createAdjustment, listAdjustments`.

### 4.3 `GoodsReceiptList.tsx`
Table of receipts with filters: status (DRAFT/COMPLETED/CANCELLED/all), supplier_id (dropdown populated via `listSuppliers`), pagination. Columns: code, supplier_name, total, paid_amount, status badge, completed_at, created_at, actions (Xem). Button "+ Nhập hàng mới" → `/goods-receipts/new`.

### 4.4 `GoodsReceiptForm.tsx`
Mode = `create` (path `/goods-receipts/new`) or `edit` (path with `:id`, but here we route edit through Detail's "Sửa nháp" button → reuse same path /goods-receipts/new with internal state; simpler: only `create` here, edit done via `update` from Detail's edit-mode toggle is **out of scope MVP**). Decision: **create-only** for `GoodsReceiptForm` to keep complexity low; backend supports PUT but UI defers it (note in `notes`).
- Supplier dropdown (from `listSuppliers`, optional).
- `ProductPicker` (reuse from Phase 2) to add line items.
- Editable table: product_name, quantity (number, step 0.001 to support kg), cost_price (VND), line_total (computed), delete row button.
- Footer: total (sum of line_totals), paid_amount input, note textarea.
- Submit → `create()` → on success navigate to `/goods-receipts/:id`.
- Error: toast via `toFriendlyMessage`.

### 4.5 `GoodsReceiptDetail.tsx`
Read-only view of a receipt + items. Buttons:
- **Hoàn tất (Complete)** — visible if `status === 'DRAFT'`. On click → confirm dialog → `complete(id)` → reload. Disable button immediately (anti double-click).
- **Hủy (Cancel)** — visible if `status === 'DRAFT'` (any role) OR `status === 'COMPLETED'` (OWNER only). On click → prompt for reason → `cancel(id, reason)` → reload.
- "← Quay lại" → `/goods-receipts`.

### 4.6 `InventoryList.tsx`
Search by name/SKU (debounced 300ms), toggle "Chỉ hiện hàng còn tồn" (only_with_stock), pagination. Columns: SKU, tên SP, đơn vị, tồn hiện tại, tồn min, giá vốn (cost), giá bán. Action: link "Xem thẻ kho" → `/inventory/:productId/movements`. Rows with `quantity <= min_stock` (and min_stock>0) show amber badge "Sắp hết".

### 4.7 `LowStock.tsx`
Simple list (no pagination — endpoint returns full set). Table: SKU, tên, đơn vị, tồn, min_stock. Empty state: "Không có sản phẩm nào sắp hết hàng."

### 4.8 `Kardex.tsx`
Route param `:productId`. Heading: "Thẻ kho — SP #{productId}" (no separate product fetch needed for MVP; movements suffice). Pagination, table columns: thời gian, loại (SALE/RECEIPT/CANCEL_SALE/CANCEL_RECEIPT/ADJUSTMENT — Vietnamese label map), tham chiếu (`ref_type #ref_id`), số lượng (signed), tồn sau, ghi chú. Color-code: green for +, red for -.

### 4.9 `AdjustmentList.tsx`
OWNER-gated list of past adjustments. Table: thời gian, SP, delta (signed), tồn sau, ghi chú, người tạo (created_by). Pagination. Header: "+ Điều chỉnh mới" → `/inventory/adjustments/new`.

### 4.10 `AdjustmentForm.tsx`
OWNER-gated. Reuse `ProductPicker` to add rows. Each row: tên SP, tồn hiện tại (need to fetch — fetched lazily via a single `inventoryApi.list({search: sku, limit: 1})` lookup at add-time and surfaced in the row), số lượng mới (input), lý do (input). Submit → `createAdjustment({items})`. Result modal shows the response items (`old_quantity → new_quantity, delta`). Then navigate back to list.

For row's current stock we use the `quantity` field from `ProductBrief`—**not available there**. Decision: at row add time, call `inventoryApi.list({search: product.sku, limit:1})` to fetch the matching inventory row; if not present, show "0".

### 4.11 Sidebar updates (`AppLayout.tsx`)
Insert items right after existing "Tồn kho":
- "Nhập kho" → `/goods-receipts`
- (already exists: "Tồn kho" → `/inventory`)
- "Điều chỉnh kho" → `/inventory/adjustments` (only show if OWNER)

## 5. State

Pages own their state via `useState`/`useEffect`. No Zustand stores added in this phase. The existing `authStore` is read to gate OWNER-only routes (`RoleGate`).

## 6. Edge cases & error handling

- **DRAFT vs COMPLETED state machine**: `complete` only on DRAFT (backend will 400/409 if violated → toast). `cancel` requires OWNER for COMPLETED — UI shows the Cancel button only when permitted; backend enforces too.
- **Insufficient stock on cancel of completed receipt**: not applicable since cancel of receipt adds quantity back. (Cancellation of *invoice* would decrement; that's Phase 4.)
- **Low-stock filter**: backend computes `quantity < min_stock AND min_stock > 0`. FE just renders.
- **Movements pagination**: default 50/page, max 200. FE uses 50.
- **Adjustments**: backend handles allow_negative based on product setting; FE allows `new_quantity = 0` (or any ≥ 0). Negative new_quantity rejected by schema (`ge=0`).
- **Anti double-spend on complete**: disable button immediately after click (per CLAUDE.md backlog #7 workaround).
- **Decimal qty**: input `step="0.001"`; we use `Number()` conversion on submit. Send as string would also be fine; we'll send numbers.
- **VND formatting**: reuse `formatVND` for total / paid_amount. `formatQty` for stock quantities.

## 7. Test plan

| Test file | Verifies |
|---|---|
| `src/api/__tests__/goodsReceipt.test.ts` | list/get/create/complete/cancel round-trips via MSW |
| `src/api/__tests__/inventory.test.ts` | list/getLowStock/getMovements/createAdjustment/listAdjustments via MSW |
| `src/pages/goodsReceipts/__tests__/GoodsReceiptList.test.tsx` | renders rows, status filter triggers fetch |
| `src/pages/goodsReceipts/__tests__/GoodsReceiptForm.test.tsx` | add line via ProductPicker, computes total, submits create, navigates |
| `src/pages/inventory/__tests__/InventoryList.test.tsx` | renders rows, low-stock badge appears |
| `src/pages/inventory/__tests__/LowStock.test.tsx` | empty state + populated |
| `src/pages/inventory/__tests__/Kardex.test.tsx` | renders movements with signed quantities |
| `src/pages/inventory/__tests__/AdjustmentForm.test.tsx` | OWNER role: can add row, submit creates adjustment |

MSW handlers extended with `/goods-receipts*` and `/inventory*` endpoints, mirroring response shapes from `inventory/schemas.py`.
