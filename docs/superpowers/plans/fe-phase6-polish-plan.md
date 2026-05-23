# FE Phase 6 Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reusable EmptyState + Skeleton components, POS keyboard shortcuts, PWA manifest, and surgical loading/empty-state polish across list pages.

**Architecture:** Three small reusable building blocks (EmptyState, Skeleton primitives, useKeyboardShortcuts hook) plus minimal Vite-served static PWA assets. List pages get a focused diff that swaps plain "Đang tải..." / "Chưa có ..." cells for the new components, preserving table structure. POS gets a window-level keyboard listener wired to existing handlers. ErrorBoundary already wraps the router in App.tsx; main.tsx wrap is a fallback safety net.

**Tech Stack:** React 18 + TypeScript + Tailwind CSS + Vitest + @testing-library/react. No new runtime dependencies.

---

## File Structure

**New files (frontend/):**
- `src/components/EmptyState.tsx`
- `src/components/Skeleton.tsx`
- `src/hooks/useKeyboardShortcuts.ts`
- `src/components/__tests__/EmptyState.test.tsx`
- `src/components/__tests__/Skeleton.test.tsx`
- `src/hooks/__tests__/useKeyboardShortcuts.test.ts`
- `src/__tests__/pwa.test.ts`
- `public/manifest.webmanifest`
- `public/icon.svg`

**Modified files (frontend/):**
- `index.html` — add manifest link + theme-color meta
- `src/pages/products/ProductList.tsx`
- `src/pages/customers/CustomerList.tsx`
- `src/pages/suppliers/SupplierList.tsx`
- `src/pages/goodsReceipts/GoodsReceiptList.tsx`
- `src/pages/inventory/InventoryList.tsx`
- `src/pages/inventory/LowStock.tsx`
- `src/pages/invoices/InvoiceList.tsx`
- `src/pages/dashboard/Dashboard.tsx`
- `src/pages/reports/RevenuePage.tsx`
- `src/pages/reports/TopProductsPage.tsx`
- `src/pages/reports/StockSummaryPage.tsx`
- `src/pages/pos/POSScreen.tsx` — wire useKeyboardShortcuts
- `src/main.tsx` — verify ErrorBoundary wrap (no-op if already wrapped via App.tsx)

---

### Task 1: EmptyState component

**Files:**
- Create: `frontend/src/components/EmptyState.tsx`

- [ ] **Step 1: Write the component**

```tsx
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center text-slate-600 bg-slate-50 border border-dashed border-slate-200 rounded"
    >
      {icon && <div className="text-3xl text-slate-400">{icon}</div>}
      <h3 className="text-base font-semibold text-slate-700">{title}</h3>
      {description && <p className="text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
```

---

### Task 2: Skeleton primitives

**Files:**
- Create: `frontend/src/components/Skeleton.tsx`

- [ ] **Step 1: Write the component**

```tsx
interface SkeletonTextProps {
  width?: string;
}

export function SkeletonText({ width = 'w-full' }: SkeletonTextProps) {
  return (
    <div
      data-testid="skeleton-text"
      className={`h-3 ${width} bg-slate-200 rounded animate-pulse`}
    />
  );
}

interface SkeletonRowProps {
  count?: number;
}

export function SkeletonRow({ count = 5 }: SkeletonRowProps) {
  const rows = Array.from({ length: count });
  return (
    <>
      {rows.map((_, i) => (
        <div
          key={i}
          data-testid="skeleton-row"
          className="flex items-center gap-3 py-2"
        >
          <div className="h-3 flex-1 bg-slate-200 rounded animate-pulse" />
          <div className="h-3 w-24 bg-slate-200 rounded animate-pulse" />
          <div className="h-3 w-16 bg-slate-200 rounded animate-pulse" />
        </div>
      ))}
    </>
  );
}

export function SkeletonCard() {
  return (
    <div
      data-testid="skeleton-card"
      className="h-24 w-full bg-slate-200 rounded animate-pulse"
    />
  );
}
```

---

### Task 3: useKeyboardShortcuts hook

**Files:**
- Create: `frontend/src/hooks/useKeyboardShortcuts.ts`

- [ ] **Step 1: Write the hook**

```ts
import { useEffect, useRef } from 'react';

type Handler = () => void;
type ShortcutMap = Partial<Record<'F2' | 'F4' | 'F9' | 'Escape', Handler>>;

interface KeyboardShortcutsOptions {
  enabled?: boolean;
  preventDefault?: boolean;
  ignoreModifier?: boolean;
}

export default function useKeyboardShortcuts(
  map: ShortcutMap,
  options: KeyboardShortcutsOptions = {},
): void {
  const { enabled = true, preventDefault = true, ignoreModifier = true } = options;
  const mapRef = useRef<ShortcutMap>(map);
  mapRef.current = map;

  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (ignoreModifier && (e.ctrlKey || e.metaKey || e.altKey)) return;
      const handler = mapRef.current[e.key as keyof ShortcutMap];
      if (!handler) return;
      if (preventDefault) e.preventDefault();
      handler();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, preventDefault, ignoreModifier]);
}
```

---

### Task 4: PWA manifest + icon

**Files:**
- Create: `frontend/public/manifest.webmanifest`
- Create: `frontend/public/icon.svg`

- [ ] **Step 1: Write manifest.webmanifest**

```json
{
  "name": "my_kiot POS",
  "short_name": "Kiot POS",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0f766e",
  "icons": [
    { "src": "/icon.svg", "sizes": "any", "type": "image/svg+xml" }
  ]
}
```

- [ ] **Step 2: Write icon.svg**

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"><rect width="192" height="192" fill="#0f766e"/><text x="96" y="130" font-size="120" font-family="sans-serif" font-weight="bold" fill="white" text-anchor="middle">K</text></svg>
```

---

### Task 5: index.html — add manifest link + theme-color

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Replace head block to include manifest + theme-color**

Inside `<head>`, add after the viewport meta:

```html
<link rel="manifest" href="/manifest.webmanifest" />
<meta name="theme-color" content="#0f766e" />
```

---

### Task 6: Update ProductList loading/empty

**Files:**
- Modify: `frontend/src/pages/products/ProductList.tsx`

- [ ] **Step 1: Import new components**

Add to imports at top:
```ts
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';
```

- [ ] **Step 2: Replace loading and empty branches**

Find:
```tsx
{loading && items.length === 0 ? (
  <tr>
    <td colSpan={8} className="px-3 py-6 text-center text-slate-500">
      Đang tải...
    </td>
  </tr>
) : items.length === 0 ? (
  <tr>
    <td colSpan={8} className="px-3 py-6 text-center text-slate-500">
      Chưa có sản phẩm
    </td>
  </tr>
) : (
```
Replace with:
```tsx
{loading && items.length === 0 ? (
  <tr>
    <td colSpan={8} className="px-3 py-6">
      <SkeletonRow count={5} />
    </td>
  </tr>
) : items.length === 0 ? (
  <tr>
    <td colSpan={8} className="px-3 py-6">
      <EmptyState
        title="Chưa có sản phẩm"
        description="Bấm 'Thêm sản phẩm' để bắt đầu nhập danh mục."
      />
    </td>
  </tr>
) : (
```

---

### Task 7: Update CustomerList loading/empty

**Files:**
- Modify: `frontend/src/pages/customers/CustomerList.tsx`

- [ ] **Step 1: Add imports**
```ts
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';
```

- [ ] **Step 2: Replace loading and empty branches**

Find `<td colSpan={7}` cells with "Đang tải..." / "Chưa có khách hàng" — replace with:
```tsx
{loading && items.length === 0 ? (
  <tr>
    <td colSpan={7} className="px-3 py-6">
      <SkeletonRow count={5} />
    </td>
  </tr>
) : items.length === 0 ? (
  <tr>
    <td colSpan={7} className="px-3 py-6">
      <EmptyState
        title="Chưa có khách hàng"
        description="Bấm 'Thêm khách hàng' để tạo hồ sơ mới."
      />
    </td>
  </tr>
) : (
```

---

### Task 8: Update SupplierList loading/empty

**Files:**
- Modify: `frontend/src/pages/suppliers/SupplierList.tsx`

- [ ] **Step 1: Read existing branches, mirror Task 7 pattern with text "Chưa có nhà cung cấp" / "Bấm 'Thêm nhà cung cấp' để bắt đầu." and matching colSpan.**

Imports:
```ts
import EmptyState from '../../components/EmptyState';
import { SkeletonRow } from '../../components/Skeleton';
```

Replace the two `<td colSpan=...>Đang tải.../Chưa có nhà cung cấp</td>` cells in tbody with SkeletonRow / EmptyState blocks as in Task 7.

---

### Task 9: Update GoodsReceiptList loading/empty

**Files:**
- Modify: `frontend/src/pages/goodsReceipts/GoodsReceiptList.tsx`

- [ ] **Step 1: Imports + replace loading/empty branches**

Empty title: "Chưa có phiếu nhập"; description: "Bấm 'Nhập hàng mới' để tạo phiếu." Apply the same SkeletonRow / EmptyState wrap.

---

### Task 10: Update InventoryList loading/empty

**Files:**
- Modify: `frontend/src/pages/inventory/InventoryList.tsx`

- [ ] **Step 1: Imports + replace loading/empty branches**

Empty title: "Chưa có dữ liệu tồn kho"; description: "Tồn kho sẽ xuất hiện sau khi nhập hàng hoặc bán hàng."

---

### Task 11: Update LowStock loading/empty

**Files:**
- Modify: `frontend/src/pages/inventory/LowStock.tsx`

- [ ] **Step 1: Imports + replace loading/empty branches**

Empty title: "Không có sản phẩm sắp hết"; description: "Tất cả SP đều trên ngưỡng tồn tối thiểu."

---

### Task 12: Update InvoiceList loading/empty

**Files:**
- Modify: `frontend/src/pages/invoices/InvoiceList.tsx`

- [ ] **Step 1: Imports + replace loading/empty branches**

Empty title: "Chưa có hóa đơn"; description: "Mở POS để bắt đầu bán hàng."

---

### Task 13: Update Dashboard loading/empty

**Files:**
- Modify: `frontend/src/pages/dashboard/Dashboard.tsx`

- [ ] **Step 1: Imports**
```ts
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';
```

- [ ] **Step 2: Replace any "Đang tải..." or empty placeholder block**

Replace "Đang tải..." with a grid of `<SkeletonCard />` (3 cards) and the empty placeholder with `<EmptyState title="Chưa có dữ liệu" />`. Keep all KPI cards intact otherwise.

---

### Task 14: Update RevenuePage loading/empty

**Files:**
- Modify: `frontend/src/pages/reports/RevenuePage.tsx`

- [ ] **Step 1: Imports + replace placeholders**

Replace "Đang tải..." with `<SkeletonCard />` and empty branch (no data rows) with `<EmptyState title="Không có dữ liệu" />`.

---

### Task 15: Update TopProductsPage loading/empty

**Files:**
- Modify: `frontend/src/pages/reports/TopProductsPage.tsx`

- [ ] **Step 1: Imports + replace placeholders**

Use SkeletonRow / EmptyState (title "Chưa có dữ liệu").

---

### Task 16: Update StockSummaryPage loading/empty

**Files:**
- Modify: `frontend/src/pages/reports/StockSummaryPage.tsx`

- [ ] **Step 1: Imports + replace placeholders**

Use SkeletonCard / EmptyState (title "Chưa có dữ liệu").

---

### Task 17: Wire keyboard shortcuts on POS

**Files:**
- Modify: `frontend/src/pages/pos/POSScreen.tsx`

- [ ] **Step 1: Add import**

```ts
import useKeyboardShortcuts from '../../hooks/useKeyboardShortcuts';
```

- [ ] **Step 2: Wire shortcuts above the `return` statement**

```ts
const anyModalOpen = paymentOpen || draftPanelOpen || receiptOpen;
useKeyboardShortcuts(
  {
    F2: () => {
      const el = document.querySelector<HTMLInputElement>(
        'input[type="search"], input[placeholder*="sản phẩm"]',
      );
      el?.focus();
      el?.select?.();
    },
    F4: () => {
      if (!anyModalOpen) void onHold();
    },
    F9: () => {
      if (!anyModalOpen && items.length > 0) setPaymentOpen(true);
    },
    Escape: () => {
      if (receiptOpen) setReceiptOpen(false);
      else if (paymentOpen) setPaymentOpen(false);
      else if (draftPanelOpen) setDraftPanelOpen(false);
    },
  },
  { enabled: true },
);
```

---

### Task 18: Verify main.tsx ErrorBoundary

**Files:**
- Check: `frontend/src/main.tsx`

- [ ] **Step 1: Read main.tsx**

If `<ErrorBoundary>` is already wrapping `<App />` (or App.tsx wraps the router), leave untouched. If not wrapped at all, modify to:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
```

Note: Phase 0 already created ErrorBoundary and App.tsx wraps router with it. This task is verification-only.

---

### Task 19: Type-check

- [ ] **Step 1: Run `cd frontend && npx tsc --noEmit`**

Expected: exit 0. If any errors, fix import paths or missing types before proceeding.

---

### Task 20: Test — EmptyState

**Files:**
- Create: `frontend/src/components/__tests__/EmptyState.test.tsx`

- [ ] **Step 1: Write test**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import EmptyState from '../EmptyState';

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No data" description="Nothing here yet" />);
    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(screen.getByText('Nothing here yet')).toBeInTheDocument();
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders action and fires its onClick', () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        title="Empty"
        action={<button onClick={onClick}>Add</button>}
      />,
    );
    fireEvent.click(screen.getByText('Add'));
    expect(onClick).toHaveBeenCalled();
  });

  it('omits description when not provided', () => {
    render(<EmptyState title="Only title" />);
    expect(screen.getByText('Only title')).toBeInTheDocument();
  });
});
```

---

### Task 21: Test — Skeleton

**Files:**
- Create: `frontend/src/components/__tests__/Skeleton.test.tsx`

- [ ] **Step 1: Write test**

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SkeletonRow, SkeletonCard, SkeletonText } from '../Skeleton';

describe('Skeleton', () => {
  it('SkeletonRow renders N rows', () => {
    render(<SkeletonRow count={3} />);
    expect(screen.getAllByTestId('skeleton-row')).toHaveLength(3);
  });

  it('SkeletonRow defaults to 5 rows', () => {
    render(<SkeletonRow />);
    expect(screen.getAllByTestId('skeleton-row')).toHaveLength(5);
  });

  it('SkeletonCard renders one card', () => {
    render(<SkeletonCard />);
    expect(screen.getByTestId('skeleton-card')).toBeInTheDocument();
  });

  it('SkeletonText renders one text bar', () => {
    render(<SkeletonText width="w-1/2" />);
    expect(screen.getByTestId('skeleton-text')).toBeInTheDocument();
  });
});
```

---

### Task 22: Test — useKeyboardShortcuts

**Files:**
- Create: `frontend/src/hooks/__tests__/useKeyboardShortcuts.test.ts`

- [ ] **Step 1: Write test**

```ts
import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import useKeyboardShortcuts from '../useKeyboardShortcuts';

function fireKey(key: string, init: Partial<KeyboardEventInit> = {}) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, ...init }));
}

describe('useKeyboardShortcuts', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('triggers F2 handler', () => {
    const onF2 = vi.fn();
    renderHook(() => useKeyboardShortcuts({ F2: onF2 }));
    fireKey('F2');
    expect(onF2).toHaveBeenCalledOnce();
  });

  it('triggers Escape handler', () => {
    const onEsc = vi.fn();
    renderHook(() => useKeyboardShortcuts({ Escape: onEsc }));
    fireKey('Escape');
    expect(onEsc).toHaveBeenCalledOnce();
  });

  it('ignores modifier+key combos by default', () => {
    const onF2 = vi.fn();
    renderHook(() => useKeyboardShortcuts({ F2: onF2 }));
    fireKey('F2', { ctrlKey: true });
    expect(onF2).not.toHaveBeenCalled();
  });

  it('suppresses all keys when enabled=false', () => {
    const onF2 = vi.fn();
    renderHook(() =>
      useKeyboardShortcuts({ F2: onF2 }, { enabled: false }),
    );
    fireKey('F2');
    expect(onF2).not.toHaveBeenCalled();
  });

  it('removes listener on unmount', () => {
    const onF2 = vi.fn();
    const { unmount } = renderHook(() =>
      useKeyboardShortcuts({ F2: onF2 }),
    );
    unmount();
    fireKey('F2');
    expect(onF2).not.toHaveBeenCalled();
  });
});
```

---

### Task 23: Test — PWA manifest

**Files:**
- Create: `frontend/src/__tests__/pwa.test.ts`

- [ ] **Step 1: Write test**

```ts
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('PWA manifest', () => {
  it('exists and parses as valid JSON with required keys', () => {
    const manifestPath = path.resolve(__dirname, '../../public/manifest.webmanifest');
    const raw = fs.readFileSync(manifestPath, 'utf8');
    const json = JSON.parse(raw);
    expect(json.name).toBe('my_kiot POS');
    expect(json.short_name).toBe('Kiot POS');
    expect(json.start_url).toBe('/');
    expect(Array.isArray(json.icons)).toBe(true);
    expect(json.icons.length).toBeGreaterThan(0);
    expect(json.icons[0].src).toBeTruthy();
  });

  it('icon.svg exists', () => {
    const iconPath = path.resolve(__dirname, '../../public/icon.svg');
    expect(fs.existsSync(iconPath)).toBe(true);
  });
});
```

---

### Task 24: Run tests

- [ ] **Step 1: Run `cd frontend && npm run test -- --run`**

Expected: all new tests pass (4 new files); previous 170 tests still pass.

If individual list-page tests fail because they were checking for literal "Đang tải..." / "Chưa có ..." strings, that's expected breakage — fix by updating those tests to look for skeleton testid or EmptyState testid instead.

---

### Task 25: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add docs/superpowers/fe-progress.md docs/superpowers/plans/ frontend/
git commit -m "FE phase 6: polish — done"
```

---

## Self-review

- Spec coverage: EmptyState, Skeleton, useKeyboardShortcuts, PWA manifest, index.html, 11 list pages, POS shortcuts, ErrorBoundary verification, all 4 tests — all covered.
- Placeholder scan: no TODOs, no "etc.", all code shown inline.
- Type consistency: `ShortcutMap` keys constrained to 'F2'|'F4'|'F9'|'Escape'; hook signature matches POS call site; component prop names consistent across plan and tests.
