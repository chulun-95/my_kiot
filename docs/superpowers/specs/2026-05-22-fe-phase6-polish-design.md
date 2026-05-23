# FE Phase 6 — Polish (Design)

**Build:** fe-build-2026-05-22
**Phase:** 6 (final)
**Topic:** polish
**Endpoints:** none (UI/UX only)

## 1. Goal

Tidy up the FE built in Phase 0-5 by adding:
1. Reusable EmptyState + Skeleton components, applied across all list pages
2. POS-only keyboard shortcuts (F2 / F4 / F9 / Escape)
3. Responsive tweaks for tablet (1024×768) on POS screen
4. ErrorBoundary verification (already in place — verify wiring)
5. Basic PWA manifest + icons + theme-color in index.html

No new backend endpoints; this phase only touches `frontend/`.

## 2. Components

### 2.1 `src/components/EmptyState.tsx`

Reusable empty-state block.

**Props:**
```ts
interface EmptyStateProps {
  icon?: React.ReactNode;       // optional symbol/SVG to display above title
  title: string;                // required headline (Vietnamese)
  description?: string;         // optional supporting copy
  action?: { label: string; onClick?: () => void; to?: string }; // optional CTA (button OR Link)
}
```

**Behavior:** Renders a centered card with neutral colors (slate-50 bg, slate-200 border). If `action.to` is set → Link; else if `onClick` → button. Test ids: `data-testid="empty-state"`.

### 2.2 `src/components/Skeleton.tsx`

Exports three primitives.

- `SkeletonText({ width? })` — single shimmer bar (default `w-full`).
- `SkeletonRow({ count = 5, cols = 1 })` — `<tr>`-like flex row repeated `count` times for use in tables (rendered as plain divs since we won't be inside a `<tbody>` always — for tables, callers wrap their own `<tr><td colSpan>...`). Actually: to keep it generic, `SkeletonRow` returns N stacked rows of N shimmer cells in a div grid, suitable for top-of-list placeholder. For tables we use a single full-width skeleton row inside the existing tbody.
- `SkeletonCard()` — 100% width × 100 px tall rounded shimmer block, used in Dashboard / StockSummary grids.

All use Tailwind `animate-pulse bg-slate-200`. No external CSS.

### 2.3 `src/hooks/useKeyboardShortcuts.ts`

Window-level keydown listener with a key→callback map.

**Signature:**
```ts
interface KeyboardShortcutsOptions {
  enabled?: boolean;                                // default true; pass false to suspend (e.g. modal open)
  preventDefault?: boolean;                          // default true
  ignoreModifier?: boolean;                          // default true: skip if ctrl/meta/alt pressed
}
function useKeyboardShortcuts(
  map: Record<string, () => void>,
  options?: KeyboardShortcutsOptions,
): void;
```

Keys correspond to `KeyboardEvent.key` values (`F2`, `F4`, `F9`, `Escape`). If `ignoreModifier` and any of `e.ctrlKey | metaKey | altKey` is true → skip. If a handler is found and `preventDefault`, `e.preventDefault()`. Uses `useRef` to keep latest map without re-binding on every change.

### 2.4 `public/manifest.webmanifest`

```json
{
  "name": "my_kiot POS",
  "short_name": "Kiot POS",
  "description": "Hệ thống POS & quản lý kho cho tạp hóa / siêu thị mini",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#0f172a",
  "lang": "vi-VN",
  "icons": [
    { "src": "/icon-192.svg", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any" },
    { "src": "/icon-512.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any" }
  ]
}
```

We'll use SVG icons (browsers accept SVG in manifests; valid spec).

### 2.5 `public/icon-192.svg`, `public/icon-512.svg`

Simple text-mark SVGs (rounded square with "KP" or similar logo text). Lightweight, no external assets.

### 2.6 `index.html` updates

Add inside `<head>`:
```html
<link rel="manifest" href="/manifest.webmanifest" />
<meta name="theme-color" content="#0f172a" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="default" />
```
Also update `<title>` to "my_kiot POS".

## 3. List pages to update

Apply pattern:
- **Loading first request** (items empty AND loading=true) → render `<SkeletonRow ... />` placeholder rows inside table body (as a single `<tr>` with `<td colSpan>` containing skeleton bars).
- **Loaded with zero items** → render `<EmptyState title="..." description="..." />` (single `<tr>`/`<td colSpan>` for tables, or block element for grids).

Targets:

| File | Empty title | Empty description |
|---|---|---|
| `pages/products/ProductList.tsx` | "Chưa có sản phẩm" | "Bấm 'Thêm sản phẩm' để bắt đầu nhập danh mục." |
| `pages/customers/CustomerList.tsx` | "Chưa có khách hàng" | "Bấm 'Thêm khách hàng' để tạo hồ sơ mới." |
| `pages/suppliers/SupplierList.tsx` | "Chưa có nhà cung cấp" | "Bấm 'Thêm nhà cung cấp' để bắt đầu." |
| `pages/goodsReceipts/GoodsReceiptList.tsx` | "Chưa có phiếu nhập" | "Bấm 'Nhập hàng mới' để tạo phiếu." |
| `pages/inventory/InventoryList.tsx` | "Chưa có dữ liệu tồn kho" | "Tồn kho sẽ xuất hiện sau khi nhập hàng hoặc bán hàng." |
| `pages/invoices/InvoiceList.tsx` | "Chưa có hóa đơn" | "Mở POS để bắt đầu bán hàng." |
| `pages/dashboard/Dashboard.tsx` | "Chưa có dữ liệu" | (single block — uses skeleton card grid while loading) |
| `pages/reports/RevenuePage.tsx` | "Không có dữ liệu" | (chart placeholder) |
| `pages/reports/TopProductsPage.tsx` | "Chưa có dữ liệu" | (chart + table placeholders) |
| `pages/reports/StockSummaryPage.tsx` | "Chưa có dữ liệu" | (skeleton card grid while loading) |

Be **surgical**: only touch the branches that currently say `"Đang tải..."` or `"Chưa có ..."`. Keep all other markup intact.

## 4. POS keyboard shortcuts

Inside `src/pages/pos/POSScreen.tsx`:

```ts
const productSearchRef = useRef<HTMLInputElement>(null);   // need to forwardRef on ProductPicker OR just query DOM
const anyModalOpen = paymentOpen || draftPanelOpen || receiptOpen;
useKeyboardShortcuts(
  {
    F2: () => {
      const el = document.querySelector<HTMLInputElement>('input[type="search"], input[aria-label*="sản phẩm"]');
      el?.focus();
      el?.select();
    },
    F4: () => { void onHold(); },
    F9: () => { if (!anyModalOpen && items.length > 0) setPaymentOpen(true); },
    Escape: () => {
      if (receiptOpen) setReceiptOpen(false);
      else if (paymentOpen) setPaymentOpen(false);
      else if (draftPanelOpen) setDraftPanelOpen(false);
    },
  },
  { enabled: true },
);
```

Note: keeping `enabled=true` always — Escape needs to fire even with modal open (to close it). For F2/F4/F9 we gate inside the handler via `anyModalOpen`.

## 5. Responsive (POS)

Current POS uses `grid-cols-12` with `md:col-span-8` (cart) and `md:col-span-4` (sidebar). At 1024×768 (md breakpoint = 768px) this layout already fits. Verify by:
- Cart table has `overflow-auto` so doesn't break.
- Sidebar has `overflow-auto` for scroll.

Add `lg:col-span-8` / `lg:col-span-4` to make the split kick in at lg (1024px) too — currently md (768) works but safer:
```diff
- col-span-12 md:col-span-8
+ col-span-12 md:col-span-7 lg:col-span-8
```
Actually a cleaner approach: keep existing `md:col-span-8/4` (already triggers at 768) — no changes needed. **Verify only**: capture in the spec that 1024×768 layout is OK because md: breakpoint kicks in at 768.

## 6. ErrorBoundary

`App.tsx` already wraps `<BrowserRouter>` in `<ErrorBoundary>` (verified at line 57). No change needed; document in spec only.

## 7. Tests

| Test file | What it asserts |
|---|---|
| `src/components/__tests__/EmptyState.test.tsx` | Renders title + description; action button click fires onClick; Link variant renders an `<a>` with correct href |
| `src/components/__tests__/Skeleton.test.tsx` | `SkeletonRow count=3` renders 3 skeleton row elements; `SkeletonCard` renders a single element; `SkeletonText` renders one |
| `src/hooks/__tests__/useKeyboardShortcuts.test.ts` | F2 triggers callback; Escape triggers; Ctrl+F2 ignored (with `ignoreModifier=true` default); `enabled=false` suppresses all |
| `src/__tests__/pwa.test.ts` | Reads `public/manifest.webmanifest` from disk via `fs.readFileSync` (node env), parses JSON, asserts `name`, `short_name`, `icons` |

PWA test runs in jsdom by default, but can use `node:fs` because vitest config already has `globals: true` and supports importing node built-ins.

## 8. Edge cases

- **Skeleton inside table:** must be a `<tr><td colSpan={N}>...skeleton...</td></tr>`. Don't break the table structure.
- **EmptyState inside table:** likewise wrap in `<tr><td colSpan={N}>`.
- **useKeyboardShortcuts unmount:** must remove listener.
- **POS Escape with no modal:** noop. Don't reset cart on Escape — too destructive.
- **Manifest icons missing:** if SVG generation fails, fall back to documenting that user should add `icon-192.png` / `icon-512.png`. We'll write SVG (always succeeds).

## 9. Acceptance criteria

- [ ] All 10 list/report pages render skeleton while loading and EmptyState when empty
- [ ] `<EmptyState />` and `<Skeleton*/>` exported from their respective files
- [ ] `useKeyboardShortcuts` hook attached on `/pos` only
- [ ] `public/manifest.webmanifest` exists and is valid JSON
- [ ] `index.html` has manifest link + theme-color meta
- [ ] `cd frontend && npx tsc --noEmit` exit 0
- [ ] All new tests pass; existing 170 tests still pass
