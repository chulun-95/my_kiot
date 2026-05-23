# FE Phase 4 — POS Sales — Design

## Goal

Build the POS (point-of-sale) screen, multi-payment checkout, draft hold/restore, invoice history, invoice detail, cancel invoice, and receipt printing — matching backend `/api/v1/invoices/*` exactly.

## Endpoints used (backend `backend/modules/sales/router.py`)

| Method | Path | Body shape | Notes |
|---|---|---|---|
| POST   | /api/v1/invoices            | `{customer_id?, items:[{product_id, quantity, unit_price?, discount_amount?}], discount_amount?, note?}` | Creates DRAFT, returns full `InvoiceResponse` |
| GET    | /api/v1/invoices            | `?page=&limit=&status=&customer_id=&cashier_id=` | Brief list + pagination |
| GET    | /api/v1/invoices/drafts     | `?mine_only=true` | Brief list (no pagination) |
| GET    | /api/v1/invoices/{id}       | — | Full detail incl. items + payments + customer/cashier name |
| PUT    | /api/v1/invoices/{id}       | `{customer_id?, items?, discount_amount?, note?}` | DRAFT only |
| POST   | /api/v1/invoices/{id}/complete | `{payments:[{method, amount, note?}], allow_debt?}` | Locks inventory, returns COMPLETED w/ change_amount, payments |
| POST   | /api/v1/invoices/{id}/cancel   | `{reason?}` | Owner can cancel COMPLETED; cashier limited to own DRAFT |

Payment methods enum: `CASH`, `BANK_TRANSFER`, `MOMO`, `VNPAY`, `OTHER`.
Status enum: `DRAFT`, `COMPLETED`, `CANCELLED`.

Error codes returned (from `service.py`):
- `INSUFFICIENT_STOCK` — `details.shortages: [{product_id, product_name, need, have}]`
- `INSUFFICIENT_PAYMENT` — `details: {total, paid}`
- `INVOICE_NOT_DRAFT`, `INVOICE_NO_ITEMS`, `PRODUCT_NOT_FOUND`, `CUSTOMER_NOT_FOUND`
- `FORBIDDEN_CANCEL_COMPLETED`, `FORBIDDEN_CANCEL_OTHERS_DRAFT`
- `ALREADY_CANCELLED`

## Routes

- `/pos` — **outside** `<AppLayout/>` wrapper but still inside `<ProtectedRoute/>`; full-screen no-sidebar layout, dedicated header bar.
- `/invoices` — inside `AppLayout`, history list with filters.
- `/invoices/:id` — inside `AppLayout`, full breakdown + Cancel button (rules per role).

## Components

### `src/pages/pos/POSScreen.tsx` (main)
Two-column grid (`grid-cols-12 gap-3 h-screen`).
- Left ~ col-span 7-8: `ProductPicker` (reused), barcode listener (`useBarcodeListener`), cart table (renders `CartLine` per item).
- Right ~ col-span 4-5: `CustomerSelectBox`, totals (subtotal, discount input, total), action buttons (Hold, Complete, Hủy).
- `DraftHoldList` rendered as a sliding panel toggled by "Hóa đơn treo" button.
- Top header with "Quay lại" link → `/dashboard`, tenant name, cashier name.
- Calls `posStore` actions; on Complete success → open `ReceiptPrint` modal + clear cart.

### `src/pages/pos/CartLine.tsx`
Props: `item` (from posStore), `onChangeQty(qty)`, `onChangeDiscount(amt)`, `onRemove()`.
Layout: row with SKU, name+unit, qty input (`step=0.001`), unit_price (display), line discount input, line_total (computed), remove button.

### `src/pages/pos/PaymentDialog.tsx`
Modal. Props: `open`, `total`, `onClose`, `onComplete(payments, allowDebt)`.
State: array of `{method, amount}` rows; user can add/remove rows. Total paid computed. Change = max(0, paid - total). If paid < total → checkbox "Cho phép nợ" (allow_debt) appears. Complete button disabled while in-flight.

### `src/pages/pos/DraftHoldList.tsx`
Props: `onRestore(invoice)`, `onClose()`.
On mount calls `listDrafts({mine_only: true})`. Displays each draft (code, total, created_at, customer name) with "Khôi phục" button.

### `src/pages/pos/CustomerSelectBox.tsx`
Wraps `CustomerQuickSearch` from Phase 2; defaults to "Khách lẻ" when null. Shows currently picked customer or "Khách lẻ".

### `src/pages/pos/ReceiptPrint.tsx`
Renders a hidden printable area (`@media print` CSS). 80mm-style: header (tenant name, address, phone), invoice code, date, cashier, items table (compact), totals, payment lines, footer (`receipt_footer` setting or default). Button "In ngay" → `window.print()`.

### `src/pages/invoices/InvoiceList.tsx`
Filters: status (DRAFT/COMPLETED/CANCELLED/all), date range (`from`/`to`), customer search by phone, cashier filter (Owner only). Paginated table with code, customer, total, status, completed_at, cashier. Row click → `/invoices/:id`.

### `src/pages/invoices/InvoiceDetail.tsx`
Loads `getInvoice(id)`. Shows full breakdown + payments table. Buttons:
- Print (always)
- Cancel — visibility per role:
  - OWNER: visible for DRAFT or COMPLETED
  - CASHIER: visible only when `status === 'DRAFT'` AND `cashier_id === current_user.id`
- Cancel triggers prompt for reason, calls `cancelInvoice`.

## Hooks / Utils

### `src/hooks/useBarcodeListener.ts`
```ts
useBarcodeListener({
  enabled: boolean,
  onScan: (code: string) => void,
  minLength?: number,    // default 8
  burstMs?: number,      // default 100
})
```
Implementation: window keydown handler; maintain `buffer` and `lastTs`. If gap > burstMs → reset. Append digits; on `Enter` if buffer length >= minLength and all digits → fire `onScan(buffer)` and reset. Ignore key events when target is `<input>` / `<textarea>` / contentEditable so it doesn't steal user typing.

## Store

### `src/stores/posStore.ts` (Zustand)
Shape:
```ts
interface CartItem {
  product_id: number;
  product_name: string;
  product_sku: string;
  unit: string;
  quantity: number;        // can be decimal (kg)
  unit_price: number;
  discount_amount: number;
}

interface PosState {
  draftId: number | null;
  customerId: number | null;
  customerName: string | null;
  items: CartItem[];
  discount: number;
  note: string;
  shortages: Array<{product_id: number; product_name: string; need: string; have: string}> | null;
  completing: boolean;
  lastCompleted: InvoiceResponse | null;
  // ops
  reset(): void;
  setCustomer(id: number | null, name: string | null): void;
  addItem(product: ProductBrief): void;
  updateQty(productId: number, qty: number): void;
  updateLineDiscount(productId: number, d: number): void;
  removeItem(productId: number): void;
  applyDiscount(d: number): void;
  setNote(n: string): void;
  hold(): Promise<void>;                              // create or update draft
  restore(draft: InvoiceResponse): void;              // load draft into cart
  complete(payments: PaymentInput[], allowDebt: boolean): Promise<InvoiceResponse>;
  subtotal(): number;
  total(): number;
}
```

Behavior:
- `addItem`: if product already in cart → qty += 1, else push new line with `unit_price = product.sale_price`.
- `hold`: if `draftId` null → call `createDraft`; else `updateDraft(draftId)`. Persist updated draft id.
- `restore`: replace store state with draft response (items map sequence).
- `complete`:
  1. Set `completing=true`.
  2. If no `draftId`: create draft first via `createDraft(items)`.
  3. Call `completeInvoice(draftId, {payments, allow_debt})`.
  4. On `INSUFFICIENT_STOCK` 400 → set `shortages` and rethrow.
  5. On success: `lastCompleted = res`, then `reset()` (but UI keeps `lastCompleted` for print).
  6. `completing=false` in `finally`.

## API mapping (`src/api/invoice.ts`)

| Function | Endpoint | Notes |
|---|---|---|
| `createDraft(payload)` | POST `/invoices` | returns InvoiceResponse |
| `updateDraft(id, payload)` | PUT `/invoices/{id}` | DRAFT only |
| `getInvoice(id)` | GET `/invoices/{id}` | |
| `listInvoices(params)` | GET `/invoices` | brief + pagination |
| `listDrafts(mineOnly?)` | GET `/invoices/drafts?mine_only=` | brief list |
| `completeInvoice(id, payload)` | POST `/invoices/{id}/complete` | `{payments, allow_debt}` |
| `cancelInvoice(id, reason?)` | POST `/invoices/{id}/cancel` | |

Types mirror backend exactly: `InvoiceItemInput`, `InvoiceItemResponse`, `PaymentInput`, `PaymentResponse`, `InvoiceBrief`, `InvoiceResponse`, `InvoiceStatus`, `PaymentMethod`.

Numeric fields tolerated as `number | string` (backend serializes Decimal as string).

## Edge cases

1. **Insufficient stock**: 400 with `error.details.shortages`. UI catches, sets `posStore.shortages`, renders a banner above cart listing each `product_name: cần X, còn Y`. Buttons remain enabled.
2. **Insufficient payment**: PaymentDialog shows "Còn thiếu X. Bật nợ để hoàn tất." with checkbox; if not checked → Complete blocked client-side; if checked → server accepts.
3. **429 rate limit**: shown via `toFriendlyMessage` (existing util uses friendly text).
4. **Double-click prevention**: PaymentDialog `Complete` button disabled while `completing` is true; POSScreen action buttons similarly disabled.
5. **Barcode listener**: only fires when target is not an editable element AND the burst gap and digit-only condition both pass. Avoids hijacking the product search input.
6. **Empty cart**: Complete & Hold are disabled.
7. **Cancel COMPLETED for CASHIER**: button not rendered.
8. **Print without browser print**: ReceiptPrint always shows on screen too; `window.print()` is a best-effort trigger.

## Test plan

API:
- `invoice.test.ts` — createDraft / listInvoices / listDrafts / getInvoice / completeInvoice / cancelInvoice all return correct shape.

Store:
- `posStore.test.ts` — addItem (new + duplicate), updateQty, removeItem, applyDiscount, subtotal/total math, hold creates new draft + sets draftId, restore replaces state, complete success path, complete with shortages sets `shortages` and rethrows.

Components:
- `POSScreen.test.tsx` — renders empty, picks a product via barcode (via the existing picker barcode handler) and shows it in cart, qty edit, customer pick, opens PaymentDialog when clicking Thanh toán.
- `PaymentDialog.test.tsx` — single CASH row sum equals total, change calc on overpay, multi-row sum, complete callback fires with payments array, debt checkbox appears when paid < total.
- `DraftHoldList.test.tsx` — renders drafts, click "Khôi phục" calls onRestore.
- `InvoiceList.test.tsx` — renders rows from API, status filter changes URL.
- `InvoiceDetail.test.tsx` — shows breakdown, Cancel button visible for OWNER on COMPLETED, hidden for CASHIER on COMPLETED.
- `useBarcodeListener.test.ts` — digit burst recognized; slow typing ignored; ignored when target is an input.

## File list

New:
- `src/api/invoice.ts`
- `src/api/__tests__/invoice.test.ts`
- `src/stores/posStore.ts`
- `src/stores/__tests__/posStore.test.ts`
- `src/pages/pos/POSScreen.tsx`
- `src/pages/pos/CartLine.tsx`
- `src/pages/pos/PaymentDialog.tsx`
- `src/pages/pos/DraftHoldList.tsx`
- `src/pages/pos/CustomerSelectBox.tsx`
- `src/pages/pos/ReceiptPrint.tsx`
- `src/pages/pos/__tests__/POSScreen.test.tsx`
- `src/pages/pos/__tests__/PaymentDialog.test.tsx`
- `src/pages/pos/__tests__/DraftHoldList.test.tsx`
- `src/pages/invoices/InvoiceList.tsx`
- `src/pages/invoices/InvoiceDetail.tsx`
- `src/pages/invoices/__tests__/InvoiceList.test.tsx`
- `src/pages/invoices/__tests__/InvoiceDetail.test.tsx`
- `src/hooks/useBarcodeListener.ts`
- `src/hooks/__tests__/useBarcodeListener.test.ts`

Modified:
- `src/App.tsx` (route `/pos` outside AppLayout, `/invoices` + `/invoices/:id` inside)
- `src/__tests__/mocks/handlers.ts` (add `/invoices/*` handlers)
