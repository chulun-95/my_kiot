# FE Phase 4 — POS Sales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the POS sales screen, multi-payment checkout, draft hold/restore, invoice history & detail, cancel-invoice, barcode listener, and 80mm receipt printing on top of the existing FE phase 0-3 scaffolding.

**Architecture:** A single full-screen `/pos` route (outside `AppLayout`) driving a Zustand `posStore` that mirrors the backend Invoice lifecycle (DRAFT → COMPLETED/CANCELLED). The store calls the new `src/api/invoice.ts` thin axios wrapper. Per-cart logic lives in the store; UI components stay dumb. `/invoices` and `/invoices/:id` live inside `AppLayout` and are plain CRUD-style pages.

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind + Zustand + axios + react-router-dom v6; tests Vitest + RTL + MSW (already configured by phase 0).

---

### Task 1: invoice API client

**Files:**
- Create: `frontend/src/api/invoice.ts`
- Test: `frontend/src/api/__tests__/invoice.test.ts`
- Modify: `frontend/src/__tests__/mocks/handlers.ts` (add `/invoices/*` handlers)

- [ ] Step 1: Add MSW handlers for `/invoices` endpoints with shapes matching `backend/modules/sales/schemas.py`.
- [ ] Step 2: Write `src/api/invoice.ts` with these exports:
  - Types: `InvoiceStatus`, `PaymentMethod`, `InvoiceItemInput`, `InvoiceItemResponse`, `PaymentInput`, `PaymentResponse`, `InvoiceBrief`, `InvoiceResponse`, `InvoiceListResponse`, `InvoiceCreatePayload`, `InvoiceUpdatePayload`, `InvoiceCompletePayload`, `ListInvoicesParams`, `Pagination`
  - Functions: `createDraft`, `updateDraft`, `getInvoice`, `listInvoices`, `listDrafts`, `completeInvoice`, `cancelInvoice` (all `apiClient`-based).
- [ ] Step 3: Write `invoice.test.ts` covering each function with the mocked responses.
- [ ] Step 4: Run `cd frontend && npm run test -- --run src/api/__tests__/invoice.test.ts`. Expected: all pass.

### Task 2: useBarcodeListener hook

**Files:**
- Create: `frontend/src/hooks/useBarcodeListener.ts`
- Test: `frontend/src/hooks/__tests__/useBarcodeListener.test.ts`

- [ ] Step 1: Implement hook signature `useBarcodeListener({ enabled, onScan, minLength = 8, burstMs = 100 })`. Uses `useEffect` to attach `window.addEventListener('keydown', ...)`. Maintains `buffer` and `lastTs` via `useRef`. Ignores when `e.target` is `INPUT`/`TEXTAREA`/`isContentEditable`. On gap > burstMs → reset buffer. Append digit chars; on `Enter` if buffer all-digit and `length >= minLength` → call `onScan(buffer)` then reset. Cleanup on unmount.
- [ ] Step 2: Test 1 — fast digit burst followed by Enter calls onScan.
- [ ] Step 3: Test 2 — slow typing (delay > burstMs) does not call onScan.
- [ ] Step 4: Test 3 — when target is an input, hook ignores keystrokes.
- [ ] Step 5: Run tests; expected pass.

### Task 3: posStore

**Files:**
- Create: `frontend/src/stores/posStore.ts`
- Test: `frontend/src/stores/__tests__/posStore.test.ts`

- [ ] Step 1: Implement store with state + actions as specified in the design spec (Section "Store"). Use `create<PosState>()`. Numeric math: `subtotal = sum(item.unit_price * qty - discount)`; `total = max(0, subtotal - discount)`.
- [ ] Step 2: `addItem` — if `product_id` exists, qty += 1; else push with `unit_price = Number(product.sale_price)`, discount 0.
- [ ] Step 3: `hold()` — call `invoiceApi.createDraft` (or `updateDraft` if `draftId` set), persist `draftId`, do NOT clear cart (so user sees hold persisted).
- [ ] Step 4: `restore(draft)` — replace items from draft response items, set `draftId`, `customerId`, `customerName`, `discount`, `note`.
- [ ] Step 5: `complete(payments, allowDebt)`:
  - If no `draftId` → `createDraft` first using current state.
  - Call `completeInvoice(draftId, {payments, allow_debt})`.
  - On axios 400 INSUFFICIENT_STOCK → extract `details.shortages` → `set({shortages})` → rethrow.
  - On success → `set({ lastCompleted: res })`, then call `reset()` (preserving `lastCompleted`).
- [ ] Step 6: Write tests covering add/dup/qty/remove/discount/subtotal/hold/restore/complete success/complete with shortage.
- [ ] Step 7: Run tests; expected pass.

### Task 4: CartLine component

**Files:**
- Create: `frontend/src/pages/pos/CartLine.tsx`

- [ ] Step 1: Pure presentational component. Props `{ item, onChangeQty, onChangeDiscount, onRemove }`. Row layout: SKU mono, name + unit, qty `<input type="number" step="0.001" min="0">`, unit price (display via `formatVND`), discount input, line total (computed `qty*unit_price - discount`, floored at 0), remove button. Use Tailwind table row styling matching `GoodsReceiptForm`.
- [ ] Step 2: No separate test file (covered via POSScreen tests).

### Task 5: CustomerSelectBox

**Files:**
- Create: `frontend/src/pages/pos/CustomerSelectBox.tsx`

- [ ] Step 1: Wrap `CustomerQuickSearch`. Props: `{ customerId, customerName, onChange(id, name) }`. Render banner showing "Khách lẻ" when null, else "{name} (phone)". Below it always render the search.

### Task 6: PaymentDialog

**Files:**
- Create: `frontend/src/pages/pos/PaymentDialog.tsx`
- Test: `frontend/src/pages/pos/__tests__/PaymentDialog.test.tsx`

- [ ] Step 1: Modal-style component (fixed overlay). Props `{ open, total, onClose, onComplete }`.
- [ ] Step 2: State: rows = `[{method: 'CASH', amount: total}]` initially. Methods dropdown for each row: CASH, BANK_TRANSFER, MOMO, VNPAY, OTHER. Add/remove row buttons.
- [ ] Step 3: Derived: `paid = sum(rows.amount)`, `change = max(0, paid - total)`, `missing = max(0, total - paid)`. When missing > 0 → show "Còn thiếu" + checkbox `allowDebt`.
- [ ] Step 4: Complete button: disabled while `submitting`. Calls `onComplete(rows.filter(r => r.amount > 0), allowDebt)` and handles loading. On error from caller (catch), surface via local `error` state with `toFriendlyMessage`.
- [ ] Step 5: Tests: renders with initial total, sum updates when amount changes, change shown when overpay, debt checkbox shown when underpay, complete callback fires with correct rows.
- [ ] Step 6: Run tests; expected pass.

### Task 7: DraftHoldList

**Files:**
- Create: `frontend/src/pages/pos/DraftHoldList.tsx`
- Test: `frontend/src/pages/pos/__tests__/DraftHoldList.test.tsx`

- [ ] Step 1: Side panel component. Props `{ onRestore, onClose }`. On mount call `invoiceApi.listDrafts(true)`, store items. Render each as a card with code, total, created_at, customer_name, "Khôi phục" button → fetch full invoice then call `onRestore(invoice)`.
- [ ] Step 2: Test: renders mocked drafts; clicking Khôi phục calls onRestore.

### Task 8: ReceiptPrint

**Files:**
- Create: `frontend/src/pages/pos/ReceiptPrint.tsx`

- [ ] Step 1: Component `{ invoice, tenant, onClose }`. Render a screen-visible card. Include a `<style>` block with `@media print { body * { visibility: hidden } .receipt, .receipt * { visibility: visible } .receipt { position: absolute; left: 0; top: 0; width: 80mm; ... } }`. Show header (tenant name, address), invoice code + created_at, items table, totals, payments, footer text.
- [ ] Step 2: "In ngay" button calls `window.print()`. "Đóng" calls onClose. No tests.

### Task 9: POSScreen

**Files:**
- Create: `frontend/src/pages/pos/POSScreen.tsx`
- Test: `frontend/src/pages/pos/__tests__/POSScreen.test.tsx`

- [ ] Step 1: Full-screen flex layout (no AppLayout sidebar). Top bar (back link, tenant name, cashier name). Left column: ProductPicker + cart table (map CartLine). Right column: CustomerSelectBox, totals (subtotal, discount input, total), action buttons (Hủy, Giữ HĐ, Thanh toán). "Hóa đơn treo" button toggles DraftHoldList overlay.
- [ ] Step 2: Use `useBarcodeListener({ enabled: true, onScan: async (code) => { try { const p = await productApi.getProductByBarcode(code); addItem(p) } catch {} } })`.
- [ ] Step 3: Shortages banner: if `posStore.shortages` non-null, render red banner listing each shortage.
- [ ] Step 4: On Thanh toán click → open `PaymentDialog`. On complete → call `posStore.complete()`, then show `ReceiptPrint` modal with `lastCompleted`. If error has INSUFFICIENT_STOCK code → keep dialog open (the store sets shortages).
- [ ] Step 5: Tests: renders empty cart message, adding a product via picker (using `aria-label='Tìm sản phẩm hoặc quét mã vạch'` from existing ProductPicker) puts it in cart, qty change updates total, payment dialog opens when clicking Thanh toán.

### Task 10: Invoice list page

**Files:**
- Create: `frontend/src/pages/invoices/InvoiceList.tsx`
- Test: `frontend/src/pages/invoices/__tests__/InvoiceList.test.tsx`

- [ ] Step 1: Page with filters (status dropdown, customer_id text, cashier_id text, page) and a paginated table. Row click → `navigate('/invoices/:id')`. Uses `invoiceApi.listInvoices(params)`.
- [ ] Step 2: Tests: renders rows from mocked list; status filter changes API call.

### Task 11: Invoice detail page

**Files:**
- Create: `frontend/src/pages/invoices/InvoiceDetail.tsx`
- Test: `frontend/src/pages/invoices/__tests__/InvoiceDetail.test.tsx`

- [ ] Step 1: Loads `invoiceApi.getInvoice(id)`. Shows breakdown table, payments, totals, customer + cashier, status badge. Cancel button visible per rules:
  - OWNER: visible if status != CANCELLED
  - CASHIER: visible if status==DRAFT && invoice.cashier_id===current_user.id
- [ ] Step 2: Clicking Cancel prompts for reason (window.prompt or inline textarea) then calls `cancelInvoice`. Print button calls `window.print()`.
- [ ] Step 3: Tests: renders breakdown; Cancel button visible for OWNER on COMPLETED; hidden for CASHIER on COMPLETED.

### Task 12: Wire routes & sidebar nav

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] Step 1: In `App.tsx`, add `/pos` route under `<ProtectedRoute />` but OUTSIDE `<AppLayout />`. Add `/invoices` and `/invoices/:id` inside the existing AppLayout block. Remove the existing Placeholder route for `/pos` and `/invoices`.
- [ ] Step 2: AppLayout sidebar already has Bán hàng (POS) and Hóa đơn entries — confirm they navigate to the new routes.

### Task 13: TypeScript check

- [ ] Step 1: Run `cd frontend && npx tsc --noEmit`. Expected exit 0. Fix any type issues.

### Task 14: Full test run

- [ ] Step 1: Run `cd frontend && npm run test -- --run --reporter=verbose`. Capture pass/fail counts. Phase target: ≥85% of new tests pass.
