# FE Phase 5 — Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Dashboard landing + 4 report pages (Revenue, TopProducts, Profit OWNER-only, StockSummary) with Recharts visualizations.

**Architecture:** Per-page local React state, Recharts ResponsiveContainer charts, OwnerOnly wrapper for Profit, shared DateRangePicker component, MSW handlers for tests.

**Tech Stack:** React 18 + TypeScript + Tailwind + Recharts + react-router-dom v6 + axios + Vitest + MSW.

---

### Task 1: API client `src/api/report.ts`

**Files:**
- Create: `frontend/src/api/report.ts`

- [ ] **Step 1: Implement typed API wrappers**

```typescript
import apiClient from './client';

export interface DashboardResponse {
  today_revenue: number | string;
  today_invoices: number;
  today_profit: number | string;
  today_customers: number;
  pending_drafts: number;
  low_stock_count: number;
  inventory_value: number | string;
}

export interface RevenuePoint {
  period: string;
  revenue: number | string;
  invoices: number;
  profit: number | string;
}

export interface RevenueResponse {
  from_date: string;
  to_date: string;
  group_by: 'day' | 'month';
  total_revenue: number | string;
  total_profit: number | string;
  total_invoices: number;
  series: RevenuePoint[];
}

export interface TopProductItem {
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity_sold: number | string;
  revenue: number | string;
  profit: number | string;
}

export interface TopProductsResponse {
  from_date: string;
  to_date: string;
  items: TopProductItem[];
}

export interface ProfitResponse {
  from_date: string;
  to_date: string;
  total_revenue: number | string;
  total_cost: number | string;
  gross_profit: number | string;
  invoices: number;
}

export interface StockSummaryResponse {
  total_products: number;
  products_in_stock: number;
  products_out_of_stock: number;
  low_stock_count: number;
  total_inventory_value: number | string;
  last_updated: string;
}

export interface DateRangeParams { from: string; to: string }

export async function getDashboard(): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>('/reports/dashboard');
  return data;
}

export async function getRevenue(params: DateRangeParams & { group_by: 'day' | 'month' }): Promise<RevenueResponse> {
  const { data } = await apiClient.get<RevenueResponse>('/reports/revenue', { params });
  return data;
}

export async function getTopProducts(params: DateRangeParams & { limit?: number }): Promise<TopProductsResponse> {
  const { data } = await apiClient.get<TopProductsResponse>('/reports/top-products', { params });
  return data;
}

export async function getProfit(params: DateRangeParams): Promise<ProfitResponse> {
  const { data } = await apiClient.get<ProfitResponse>('/reports/profit', { params });
  return data;
}

export async function getStockSummary(): Promise<StockSummaryResponse> {
  const { data } = await apiClient.get<StockSummaryResponse>('/reports/stock-summary');
  return data;
}
```

- [ ] **Step 2: Commit (deferred — single end-of-phase commit per runbook)**

### Task 2: Extend MSW handlers for `/reports/*`

**Files:**
- Modify: `frontend/src/__tests__/mocks/handlers.ts` (append before closing `]`)

- [ ] **Step 1: Add handlers**

```typescript
  // ---------- REPORTS ----------
  http.get('*/reports/dashboard', () =>
    HttpResponse.json({
      today_revenue: 1500000,
      today_invoices: 12,
      today_profit: 450000,
      today_customers: 8,
      pending_drafts: 2,
      low_stock_count: 3,
      inventory_value: 25000000,
    }),
  ),
  http.get('*/reports/revenue', ({ request }) => {
    const url = new URL(request.url);
    const from = url.searchParams.get('from') ?? '2026-04-23';
    const to = url.searchParams.get('to') ?? '2026-05-23';
    const groupBy = (url.searchParams.get('group_by') ?? 'day') as 'day' | 'month';
    return HttpResponse.json({
      from_date: from,
      to_date: to,
      group_by: groupBy,
      total_revenue: 3000000,
      total_profit: 900000,
      total_invoices: 25,
      series: [
        { period: '2026-05-21', revenue: 1000000, invoices: 10, profit: 300000 },
        { period: '2026-05-22', revenue: 1200000, invoices: 8, profit: 360000 },
        { period: '2026-05-23', revenue: 800000, invoices: 7, profit: 240000 },
      ],
    });
  }),
  http.get('*/reports/top-products', ({ request }) => {
    const url = new URL(request.url);
    const from = url.searchParams.get('from') ?? '2026-04-23';
    const to = url.searchParams.get('to') ?? '2026-05-23';
    return HttpResponse.json({
      from_date: from,
      to_date: to,
      items: [
        {
          product_id: 1,
          product_sku: 'SP000001',
          product_name: 'Mì tôm Hảo Hảo',
          quantity_sold: 120,
          revenue: 600000,
          profit: 180000,
        },
        {
          product_id: 2,
          product_sku: 'SP000002',
          product_name: 'Coca 330ml',
          quantity_sold: 80,
          revenue: 560000,
          profit: 140000,
        },
      ],
    });
  }),
  http.get('*/reports/profit', ({ request }) => {
    const url = new URL(request.url);
    return HttpResponse.json({
      from_date: url.searchParams.get('from') ?? '2026-04-23',
      to_date: url.searchParams.get('to') ?? '2026-05-23',
      total_revenue: 3000000,
      total_cost: 2100000,
      gross_profit: 900000,
      invoices: 25,
    });
  }),
  http.get('*/reports/stock-summary', () =>
    HttpResponse.json({
      total_products: 50,
      products_in_stock: 45,
      products_out_of_stock: 5,
      low_stock_count: 3,
      total_inventory_value: 25000000,
      last_updated: '2026-05-23T09:00:00Z',
    }),
  ),
```

### Task 3: `DateRangePicker` component

**Files:**
- Create: `frontend/src/components/DateRangePicker.tsx`

```typescript
import dayjs from 'dayjs';

export interface DateRange { from: string; to: string }

export function defaultRangeLast30(): DateRange {
  const to = dayjs().format('YYYY-MM-DD');
  const from = dayjs().subtract(30, 'day').format('YYYY-MM-DD');
  return { from, to };
}

interface Props {
  value: DateRange;
  onChange: (next: DateRange) => void;
}

export default function DateRangePicker({ value, onChange }: Props) {
  const invalid = value.from && value.to && value.from > value.to;
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-sm">
        <span className="block text-slate-600 mb-1">Từ ngày</span>
        <input
          type="date"
          aria-label="Từ ngày"
          value={value.from}
          onChange={(e) => onChange({ ...value, from: e.target.value })}
          className="border border-slate-300 rounded px-2 py-1"
        />
      </label>
      <label className="text-sm">
        <span className="block text-slate-600 mb-1">Đến ngày</span>
        <input
          type="date"
          aria-label="Đến ngày"
          value={value.to}
          onChange={(e) => onChange({ ...value, to: e.target.value })}
          className="border border-slate-300 rounded px-2 py-1"
        />
      </label>
      {invalid && (
        <span role="alert" className="text-sm text-rose-600">
          Khoảng ngày không hợp lệ
        </span>
      )}
    </div>
  );
}
```

### Task 4: Dashboard page

**Files:**
- Create: `frontend/src/pages/dashboard/Dashboard.tsx`

Renders the 6 KPI cards. Use `formatVND` and `formatDate`. On error use `toFriendlyMessage`. Low-stock card links to `/inventory/low-stock`.

### Task 5: RevenuePage

**Files:**
- Create: `frontend/src/pages/reports/RevenuePage.tsx`

- Local state: `range`, `groupBy`, `data`, `loading`, `error`
- On mount + "Xem báo cáo" click → call `getRevenue`
- Recharts `<LineChart>` inside fixed-size container (`width=600 height=300`) — we avoid `<ResponsiveContainer>` to ensure jsdom rendering and avoid layout flicker in tests; in real browser, the chart is wrapped by a div with `w-full overflow-x-auto`.

### Task 6: TopProductsPage

**Files:**
- Create: `frontend/src/pages/reports/TopProductsPage.tsx`

- Date picker + limit select
- Recharts `<BarChart>` (fixed dims)
- Table with SKU, name, qty, revenue, profit

### Task 7: ProfitPage (OWNER-only via router)

**Files:**
- Create: `frontend/src/pages/reports/ProfitPage.tsx`

- Date picker + summary table; margin% computed `gross_profit / total_revenue * 100`.

### Task 8: StockSummaryPage

**Files:**
- Create: `frontend/src/pages/reports/StockSummaryPage.tsx`

- Tiles: total/in/out/low/value/last_updated

### Task 9: Wire routes + nav

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

- App.tsx: replace `<Placeholder title="Tổng quan" />` with `<Dashboard />`; replace `/reports/revenue` placeholder; add `/reports/top-products`, `/reports/profit` (OwnerOnly), `/reports/stock-summary`.
- AppLayout.tsx: replace "Báo cáo" item with "Doanh thu", "Top SP", "Tồn kho TQ"; OWNER also sees "Lợi nhuận".

### Task 10: Tests

**Files:**
- Create: `frontend/src/api/__tests__/report.test.ts`
- Create: `frontend/src/components/__tests__/DateRangePicker.test.tsx`
- Create: `frontend/src/pages/dashboard/__tests__/Dashboard.test.tsx`
- Create: `frontend/src/pages/reports/__tests__/RevenuePage.test.tsx`
- Create: `frontend/src/pages/reports/__tests__/TopProductsPage.test.tsx`
- Create: `frontend/src/pages/reports/__tests__/ProfitPage.test.tsx`
- Create: `frontend/src/pages/reports/__tests__/StockSummaryPage.test.tsx`

Each follows existing patterns (MemoryRouter + render, MSW backed). Profit test stamps authStore with OWNER then asserts content; CASHIER block tested via direct render of OwnerOnly wrapper.

### Task 11: Verify

- [ ] `cd frontend && npx tsc --noEmit` exits 0
- [ ] `cd frontend && npm run test -- --run` reports all green

### Self-Review

- All endpoints from spec mapped to api/report.ts: yes.
- DateRangePicker tested: yes.
- Profit OwnerOnly gating: yes (router-level wrapper).
- group_by limited to day/month (BE constraint): yes.
- Empty states: rendered as text fallback in each page.
- No placeholders or "TBD" remain.
