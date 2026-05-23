# FE Phase 5 — Reports — Design

## Goal

Implement the Reports module for `my_kiot` FE: a dashboard landing page (post-login) and four report views. Charts use Recharts (already installed in Phase 0). All pages live inside `AppLayout`; `/reports/profit` is OWNER-only.

## Backend endpoints (verified from `backend/modules/report/router.py`)

| Method | Path | Auth | Query params |
|---|---|---|---|
| GET | `/api/v1/reports/dashboard` | OWNER | — |
| GET | `/api/v1/reports/revenue` | OWNER | `from` (date), `to` (date), `group_by` ∈ `{day, month}` |
| GET | `/api/v1/reports/top-products` | OWNER | `from`, `to`, `limit` (1..100, default 10) |
| GET | `/api/v1/reports/profit` | OWNER | `from`, `to` |
| GET | `/api/v1/reports/stock-summary` | OWNER | — |

Backend `require_role("OWNER")` means CASHIER receives 403. FE must still render OwnerOnly wrappers for nicer UX (no error toast on landing).

> **Important:** backend `group_by` only supports `day` or `month`. The original task brief mentioned "day/week/month" — FE will offer only `day` and `month` to match BE truth.

## Routes (react-router-dom v6)

All routes live INSIDE `AppLayout` under `ProtectedRoute`.

| Path | Component | Gated |
|---|---|---|
| `/dashboard` | `Dashboard` | OWNER backend; FE renders empty/no-data for CASHIER (403 → friendly message) |
| `/reports/revenue` | `RevenuePage` | (same as above) |
| `/reports/top-products` | `TopProductsPage` | |
| `/reports/profit` | `ProfitPage` | wrapped in `OwnerOnly` FE-side |
| `/reports/stock-summary` | `StockSummaryPage` | |

`App.tsx` change: `/dashboard` placeholder → real `Dashboard`. The existing `/reports/revenue` placeholder is replaced.

## Components & responsibilities

### `src/api/report.ts`
Typed wrappers around the 5 endpoints. Exports `getDashboard`, `getRevenue(params)`, `getTopProducts(params)`, `getProfit(params)`, `getStockSummary`. Types match BE schemas in `backend/modules/report/schemas.py` (Decimal arrives as string from FastAPI Pydantic v2 default).

### `src/components/DateRangePicker.tsx`
Controlled two-input picker (`from` + `to`, type=`date`). Props: `{ from: string; to: string; onChange: (next: { from: string; to: string }) => void }`. Helper `defaultRangeLast30()` returns `{ from: today-30d, to: today }` (ISO `YYYY-MM-DD`). Component does not auto-fetch; parent owns submit.

### `src/pages/dashboard/Dashboard.tsx`
Card grid (responsive `grid-cols-1 md:grid-cols-2 xl:grid-cols-4`):
1. Doanh thu hôm nay (`today_revenue` → `formatVND`)
2. Số hóa đơn hôm nay (`today_invoices`)
3. Lợi nhuận hôm nay (`today_profit` — visible to OWNER only; backend gates entire endpoint)
4. Hóa đơn nháp (`pending_drafts`)
5. Hàng sắp hết (`low_stock_count`) — linkable to `/inventory/low-stock`
6. Giá trị tồn kho (`inventory_value`)

On 403/error: show friendly message (`toFriendlyMessage`). Empty data → still shows cards with `0`.

### `src/pages/reports/RevenuePage.tsx`
- Header + `DateRangePicker` + `group_by` `<select>` (`day` | `month`) + "Xem báo cáo" button
- Summary tiles: total_revenue, total_profit, total_invoices
- Recharts `<LineChart>` with `<ResponsiveContainer width="100%" height={320}>` plotting `series[].revenue` vs `period`. Tooltip uses `formatVND`.
- Empty state: "Không có dữ liệu trong khoảng thời gian này"
- Submit button triggers re-fetch (deferred-fetch pattern: form state, then call API).

### `src/pages/reports/TopProductsPage.tsx`
- Date range + limit `<select>` (5, 10, 20, 50)
- Recharts `<BarChart>` showing top 10 by revenue (vertical bars, x = `product_name`, y = `revenue`)
- Table below: SKU, Tên SP, SL bán, Doanh thu (VND), Lợi nhuận (VND)
- Empty state.

### `src/pages/reports/ProfitPage.tsx`
- Wrapped at router-level by `OwnerOnly`. Page assumes OWNER role.
- Date range picker.
- Summary table with: from, to, total_revenue, total_cost, gross_profit, invoices, gross margin %.

### `src/pages/reports/StockSummaryPage.tsx`
- Auto-loads on mount.
- Tiles: total_products, products_in_stock, products_out_of_stock, low_stock_count, total_inventory_value (formatVND), last_updated (formatDate).
- Link to `/inventory/low-stock` from low-stock tile.

### `AppLayout.tsx` nav update
Replace single "Báo cáo" item with explicit links: "Tổng quan" → `/dashboard` (already exists), "Doanh thu" → `/reports/revenue`, "Top SP" → `/reports/top-products`, "Tồn kho TQ" → `/reports/stock-summary`. OWNER also sees "Lợi nhuận" → `/reports/profit`.

## State

No new Zustand stores. Each page owns local React state:
- `range` (`{from, to}` strings)
- `groupBy` (RevenuePage)
- `limit` (TopProductsPage)
- `data` (typed response)
- `loading`, `error`

## API mapping

| Endpoint | Component | Request | Response handling |
|---|---|---|---|
| GET /reports/dashboard | Dashboard | none | Decimals → `formatVND` |
| GET /reports/revenue | RevenuePage | `from=YYYY-MM-DD&to=YYYY-MM-DD&group_by=day\|month` | series mapped to chart data, totals to tiles |
| GET /reports/top-products | TopProductsPage | `from,to,limit` | items[] → chart + table |
| GET /reports/profit | ProfitPage (OwnerOnly) | `from,to` | rendered into summary table |
| GET /reports/stock-summary | StockSummaryPage | none | tiles |

## Edge cases & errors

- **Empty data:** dashboard cards render `0` / VND `0 đ`; chart pages show empty-state text "Không có dữ liệu".
- **Date default:** `defaultRangeLast30()` — last 30 days.
- **Invalid range:** if user picks `from > to`, FE disables submit + shows red helper text (BE returns 400 `INVALID_DATE_RANGE` anyway).
- **OWNER-only profit page:** wrapped in `<OwnerOnly>` (reuses pattern from Phase 3 — `RoleGate` with fallback message). CASHIER sees "Không có quyền truy cập".
- **403 from BE on non-Profit pages:** treat as friendly error message via `toFriendlyMessage`.
- **Timezone display:** `formatDate` already converts to `Asia/Ho_Chi_Minh` via dayjs (`format.ts`).
- **Chart sizing:** Recharts requires `<ResponsiveContainer>` (with explicit `height`) to render in jsdom; tests use mocked container by setting fixed dimensions (we use `width={500} height={300}` inline for jsdom predictability when ResponsiveContainer detection is unreliable — but for browser we keep ResponsiveContainer).

## Test plan

| File | Behavior |
|---|---|
| `api/__tests__/report.test.ts` | All 5 endpoints round-trip via MSW; query params forwarded for revenue/top-products/profit |
| `pages/dashboard/__tests__/Dashboard.test.tsx` | Cards render with formatted VND from mock; "Giá trị tồn kho" tile visible |
| `pages/reports/__tests__/RevenuePage.test.tsx` | After click "Xem báo cáo" re-fetches; total revenue formatted; chart container present |
| `pages/reports/__tests__/TopProductsPage.test.tsx` | Table rows render product SKU + name + revenue |
| `pages/reports/__tests__/ProfitPage.test.tsx` | OWNER renders revenue/cost/profit; CASHIER blocked (test via authStore.user.role=CASHIER + OwnerOnly wrapper) |
| `pages/reports/__tests__/StockSummaryPage.test.tsx` | Renders tiles with correct numbers and VND |
| `components/__tests__/DateRangePicker.test.tsx` | Controlled inputs; onChange callback fires |

## Files to create

```
src/api/report.ts
src/components/DateRangePicker.tsx
src/components/__tests__/DateRangePicker.test.tsx
src/pages/dashboard/Dashboard.tsx
src/pages/dashboard/__tests__/Dashboard.test.tsx
src/pages/reports/RevenuePage.tsx
src/pages/reports/TopProductsPage.tsx
src/pages/reports/ProfitPage.tsx
src/pages/reports/StockSummaryPage.tsx
src/pages/reports/__tests__/RevenuePage.test.tsx
src/pages/reports/__tests__/TopProductsPage.test.tsx
src/pages/reports/__tests__/ProfitPage.test.tsx
src/pages/reports/__tests__/StockSummaryPage.test.tsx
src/api/__tests__/report.test.ts
```

## Files to modify

```
src/App.tsx         (mount real Dashboard, add /reports/* routes)
src/components/AppLayout.tsx  (replace single "Báo cáo" link with explicit report links)
src/__tests__/mocks/handlers.ts (add /reports/* handlers)
```
