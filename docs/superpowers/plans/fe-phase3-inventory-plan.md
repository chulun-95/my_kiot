# FE Phase 3 — Inventory & Goods Receipts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Goods Receipt CRUD + Inventory listing/kardex + OWNER-only stocktake adjustments to the my_kiot frontend.

**Architecture:** Two API modules (`goodsReceipt.ts`, `inventory.ts`) + page-owned state. Reuse `ProductPicker`, `RoleGate`, `formatVND`, `formatQty` from earlier phases. No new Zustand stores. Vietnamese UI, Tailwind utilities, react-router v6.

**Tech Stack:** React 18, TypeScript, axios, react-router-dom v6, Tailwind, Vitest + RTL + MSW.

---

## File map

**New files:**
- `frontend/src/api/goodsReceipt.ts`
- `frontend/src/api/inventory.ts`
- `frontend/src/api/__tests__/goodsReceipt.test.ts`
- `frontend/src/api/__tests__/inventory.test.ts`
- `frontend/src/pages/goodsReceipts/GoodsReceiptList.tsx`
- `frontend/src/pages/goodsReceipts/GoodsReceiptForm.tsx`
- `frontend/src/pages/goodsReceipts/GoodsReceiptDetail.tsx`
- `frontend/src/pages/goodsReceipts/__tests__/GoodsReceiptList.test.tsx`
- `frontend/src/pages/goodsReceipts/__tests__/GoodsReceiptForm.test.tsx`
- `frontend/src/pages/inventory/InventoryList.tsx`
- `frontend/src/pages/inventory/LowStock.tsx`
- `frontend/src/pages/inventory/Kardex.tsx`
- `frontend/src/pages/inventory/AdjustmentList.tsx`
- `frontend/src/pages/inventory/AdjustmentForm.tsx`
- `frontend/src/pages/inventory/__tests__/InventoryList.test.tsx`
- `frontend/src/pages/inventory/__tests__/LowStock.test.tsx`
- `frontend/src/pages/inventory/__tests__/Kardex.test.tsx`
- `frontend/src/pages/inventory/__tests__/AdjustmentForm.test.tsx`

**Modified files:**
- `frontend/src/App.tsx` — add Phase 3 routes
- `frontend/src/components/AppLayout.tsx` — sidebar items
- `frontend/src/__tests__/mocks/handlers.ts` — add goods-receipts + inventory handlers

---

### Task 1: API layer — `goodsReceipt.ts`

**Files:**
- Create: `frontend/src/api/goodsReceipt.ts`

- [ ] **Step 1:** Define TypeScript types matching `backend/modules/inventory/schemas.py` for `GoodsReceiptResponse`, brief, items, create/update payloads, list response, status enum.

- [ ] **Step 2:** Export functions: `list`, `get`, `create`, `update`, `complete`, `cancel` using shared `apiClient` axios instance.

- [ ] **Step 3:** Commit.

### Task 2: API layer — `inventory.ts`

**Files:**
- Create: `frontend/src/api/inventory.ts`

- [ ] **Step 1:** Define types: `InventoryItem`, `LowStockItem`, `StockMovement`, `AdjustmentItem`, `AdjustmentResultItem`, `AdjustmentMovement`, lists + pagination.

- [ ] **Step 2:** Export `list`, `getLowStock`, `getMovements(productId, params)`, `createAdjustment(payload)`, `listAdjustments(params)`.

- [ ] **Step 3:** Commit.

### Task 3: MSW handlers extension

**Files:**
- Modify: `frontend/src/__tests__/mocks/handlers.ts`

- [ ] **Step 1:** Add handlers for goods-receipts CRUD + complete + cancel, returning shapes matching schemas.

- [ ] **Step 2:** Add handlers for inventory list, low-stock, movements, adjustments POST + GET.

- [ ] **Step 3:** Verify existing handlers untouched.

### Task 4: API tests

**Files:**
- Create: `frontend/src/api/__tests__/goodsReceipt.test.ts`
- Create: `frontend/src/api/__tests__/inventory.test.ts`

- [ ] **Step 1:** Test round-trip for each function — pass dummy payload, assert returned shape.

### Task 5: GoodsReceiptList page

**Files:**
- Create: `frontend/src/pages/goodsReceipts/GoodsReceiptList.tsx`

- [ ] **Step 1:** Table with status filter, supplier filter, pagination, new-receipt button. Use `goodsReceiptApi.list`.

### Task 6: GoodsReceiptForm page (create-mode)

**Files:**
- Create: `frontend/src/pages/goodsReceipts/GoodsReceiptForm.tsx`

- [ ] **Step 1:** Supplier dropdown via `listSuppliers`. `ProductPicker` to add line items.
- [ ] **Step 2:** Editable lines table (quantity, cost_price). Total computed. Submit → `create()` → navigate to detail.

### Task 7: GoodsReceiptDetail page

**Files:**
- Create: `frontend/src/pages/goodsReceipts/GoodsReceiptDetail.tsx`

- [ ] **Step 1:** Fetch receipt by id, render header + items.
- [ ] **Step 2:** Complete button (DRAFT only) with disable-on-click. Cancel button (DRAFT any, COMPLETED OWNER only) with reason prompt.

### Task 8: InventoryList page

**Files:**
- Create: `frontend/src/pages/inventory/InventoryList.tsx`

- [ ] **Step 1:** Search + only_with_stock toggle, pagination. Low-stock amber badge for `quantity<=min_stock && min_stock>0`. Action link to kardex.

### Task 9: LowStock page

**Files:**
- Create: `frontend/src/pages/inventory/LowStock.tsx`

- [ ] **Step 1:** Render `inventoryApi.getLowStock()` list with empty state.

### Task 10: Kardex page

**Files:**
- Create: `frontend/src/pages/inventory/Kardex.tsx`

- [ ] **Step 1:** Read `:productId`, fetch movements paginated, render timeline table with signed qty colors + type label map.

### Task 11: AdjustmentList page

**Files:**
- Create: `frontend/src/pages/inventory/AdjustmentList.tsx`

- [ ] **Step 1:** OWNER-gated. Fetch `listAdjustments`, render table.

### Task 12: AdjustmentForm page

**Files:**
- Create: `frontend/src/pages/inventory/AdjustmentForm.tsx`

- [ ] **Step 1:** OWNER-gated. `ProductPicker` adds rows; on add, lookup current stock via `inventoryApi.list({search: sku, limit:1})`.
- [ ] **Step 2:** Submit → `createAdjustment({items})`, show result modal with old → new.

### Task 13: Wire routes + sidebar

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1:** Add `/goods-receipts`, `/goods-receipts/new`, `/goods-receipts/:id`, replace `/inventory` placeholder with `InventoryList`, add `/inventory/low-stock`, `/inventory/:productId/movements`, `/inventory/adjustments`, `/inventory/adjustments/new` (RoleGate OWNER).
- [ ] **Step 2:** Add sidebar items: "Nhập kho" (before existing Tồn kho or after), "Điều chỉnh kho" (OWNER-only).

### Task 14: Page tests

**Files:**
- Create: `frontend/src/pages/goodsReceipts/__tests__/GoodsReceiptList.test.tsx`
- Create: `frontend/src/pages/goodsReceipts/__tests__/GoodsReceiptForm.test.tsx`
- Create: `frontend/src/pages/inventory/__tests__/InventoryList.test.tsx`
- Create: `frontend/src/pages/inventory/__tests__/LowStock.test.tsx`
- Create: `frontend/src/pages/inventory/__tests__/Kardex.test.tsx`
- Create: `frontend/src/pages/inventory/__tests__/AdjustmentForm.test.tsx`

- [ ] **Step 1:** Smoke tests (render + at least one user interaction per page).

### Task 15: Verify

- [ ] `cd frontend && npx tsc --noEmit` → exit 0
- [ ] `cd frontend && npm run test -- --run` → record pass/fail
- [ ] Commit.
