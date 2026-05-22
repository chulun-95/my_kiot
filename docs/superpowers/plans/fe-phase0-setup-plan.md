# FE Phase 0 — Setup khung FE Implementation Plan

> **For agentic workers:** Autonomous execution. Steps use checkbox syntax for tracking only.

**Goal:** Stand up a Vite + React + TS + Tailwind frontend with axios JWT-refresh client, Zustand auth store, layout shell, route protection, format/error utilities, Vitest+MSW harness, and smoke tests.

**Architecture:** Single-page React app under `frontend/`. Auth = in-memory access token (XSS hardening) + httpOnly refresh cookie. Routing via react-router-dom v6 with `ProtectedRoute` guard wrapping `AppLayout`. Domain Zustand stores in `src/stores/`. Errors translated to Vietnamese via `utils/errors.ts`.

**Tech Stack:** Vite 5 + React 18 + TypeScript 5 + Tailwind 3 + Zustand + react-router-dom 6 + axios + dayjs + Recharts. Tests: Vitest + @testing-library/react + MSW + jsdom.

---

## File Structure

```
frontend/
├── package.json                 (created by Vite, modified for scripts/deps)
├── tsconfig.json                (Vite scaffold)
├── tsconfig.node.json           (Vite scaffold)
├── vite.config.ts               (Vite scaffold)
├── vitest.config.ts             (new)
├── tailwind.config.js           (npx tailwindcss init)
├── postcss.config.js            (npx tailwindcss init)
├── index.html                   (Vite scaffold, title tweak)
├── .env.example                 (new — VITE_API_BASE_URL)
├── src/
│   ├── main.tsx                 (Vite scaffold, modified)
│   ├── App.tsx                  (rewritten — router config)
│   ├── index.css                (rewritten — tailwind directives)
│   ├── vite-env.d.ts            (Vite scaffold)
│   ├── api/
│   │   └── client.ts            (new — axios + refresh interceptor)
│   ├── stores/
│   │   └── authStore.ts         (new — Zustand)
│   ├── components/
│   │   ├── AppLayout.tsx        (new — sidebar+topbar+outlet)
│   │   ├── ProtectedRoute.tsx   (new)
│   │   ├── RoleGate.tsx         (new)
│   │   └── ErrorBoundary.tsx    (new — light version)
│   ├── utils/
│   │   ├── format.ts            (new — VND, date, qty)
│   │   ├── errors.ts            (new — BE error mapper)
│   │   └── __tests__/
│   │       ├── format.test.ts   (new — smoke)
│   │       └── errors.test.ts   (new — smoke)
│   └── __tests__/
│       ├── setup.ts             (new — testing-library/jest-dom)
│       └── mocks/
│           └── handlers.ts      (new — empty MSW starter)
```

---

## Task 1: Scaffold Vite project & install dependencies

**Files:**
- Create: `frontend/` (whole tree via Vite generator)

- [ ] Step 1: Generate Vite project (non-interactive)
  Run: `npm create vite@latest frontend -- --template react-ts`
  Expected: `frontend/` created with package.json, vite.config.ts, src/, index.html, tsconfig.json.

- [ ] Step 2: Install base deps
  Run: `cd frontend && npm install`

- [ ] Step 3: Install runtime deps
  Run: `cd frontend && npm i axios zustand react-router-dom dayjs recharts`

- [ ] Step 4: Install dev deps
  Run: `cd frontend && npm i -D tailwindcss postcss autoprefixer vitest @vitest/coverage-v8 @testing-library/react @testing-library/jest-dom jsdom msw @types/node`

- [ ] Step 5: Initialize Tailwind
  Run: `cd frontend && npx tailwindcss init -p`
  Expected: `tailwind.config.js` and `postcss.config.js` created.

---

## Task 2: Configure Tailwind

**Files:**
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/src/index.css`

- [ ] Step 1: Replace `frontend/tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
};
```

- [ ] Step 2: Replace `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
body { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
```

---

## Task 3: package.json scripts + .env.example

**Files:**
- Modify: `frontend/package.json` (scripts section)
- Create: `frontend/.env.example`

- [ ] Step 1: Add test script to package.json (next to existing dev/build/preview)

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "test": "vitest"
}
```
(Preserve any existing build / lint as scaffolded; ensure `test` exists.)

- [ ] Step 2: Create `frontend/.env.example`

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## Task 4: Vitest config + test setup

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/__tests__/setup.ts`
- Create: `frontend/src/__tests__/mocks/handlers.ts`

- [ ] Step 1: Create `frontend/vitest.config.ts`

```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    css: false,
  },
});
```

- [ ] Step 2: Create `frontend/src/__tests__/setup.ts`

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] Step 3: Create `frontend/src/__tests__/mocks/handlers.ts`

```ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.post('*/auth/refresh', () => HttpResponse.json({ access_token: 'mock-access-token' })),
];
```

---

## Task 5: Zustand auth store

**Files:**
- Create: `frontend/src/stores/authStore.ts`

- [ ] Step 1: Create the store

```ts
import { create } from 'zustand';

export type Role = 'OWNER' | 'CASHIER';

export interface User {
  id: number;
  full_name: string;
  role: Role;
  phone?: string | null;
  email?: string | null;
}

export interface Tenant {
  id: number;
  name: string;
  slug: string;
}

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  accessToken: string | null;
  setAuth: (payload: { user: User; tenant: Tenant; accessToken: string }) => void;
  setUser: (user: User) => void;
  setAccessToken: (token: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tenant: null,
  accessToken: null,
  setAuth: ({ user, tenant, accessToken }) => set({ user, tenant, accessToken }),
  setUser: (user) => set({ user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  logout: () => set({ user: null, tenant: null, accessToken: null }),
}));
```

---

## Task 6: Axios client with JWT refresh interceptor

**Files:**
- Create: `frontend/src/api/client.ts`

- [ ] Step 1: Create client

```ts
import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import { useAuthStore } from '../stores/authStore';

const baseURL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api/v1';

export const apiClient = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const res = await axios.post(
        `${baseURL}/auth/refresh`,
        {},
        { withCredentials: true, headers: { 'X-Requested-With': 'XMLHttpRequest' } },
      );
      const token = (res.data?.access_token as string) || null;
      if (token) useAuthStore.getState().setAccessToken(token);
      return token;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    const status = error.response?.status;
    const url = original?.url || '';
    if (status === 401 && original && !original._retry && !url.includes('/auth/refresh') && !url.includes('/auth/login')) {
      original._retry = true;
      const newToken = await refreshAccessToken();
      if (newToken) {
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>).Authorization = `Bearer ${newToken}`;
        return apiClient.request(original);
      }
      useAuthStore.getState().logout();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
```

---

## Task 7: Format utilities

**Files:**
- Create: `frontend/src/utils/format.ts`

- [ ] Step 1: Create the file

```ts
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

const TZ = 'Asia/Ho_Chi_Minh';
const vndFormatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 });

export function formatVND(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') return '0 đ';
  const n = typeof amount === 'string' ? Number(amount) : amount;
  if (!Number.isFinite(n)) return '0 đ';
  return `${vndFormatter.format(Math.round(n))} đ`;
}

export function formatDate(value: string | Date | null | undefined, fmt: string = 'DD/MM/YYYY HH:mm'): string {
  if (!value) return '';
  const d = dayjs(value);
  if (!d.isValid()) return '';
  try {
    return d.tz(TZ).format(fmt);
  } catch {
    return d.format(fmt);
  }
}

export function formatQty(qty: number | string | null | undefined): string {
  if (qty === null || qty === undefined || qty === '') return '0';
  const n = typeof qty === 'string' ? Number(qty) : qty;
  if (!Number.isFinite(n)) return '0';
  const fixed = n.toFixed(3);
  return fixed.replace(/\.?0+$/, '');
}
```

---

## Task 8: Error utilities

**Files:**
- Create: `frontend/src/utils/errors.ts`

- [ ] Step 1: Create the file

```ts
import { AxiosError } from 'axios';

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

const FRIENDLY: Record<string, string> = {
  INSUFFICIENT_STOCK: 'Số lượng tồn không đủ',
  INVALID_CREDENTIALS: 'Sai số điện thoại hoặc mật khẩu',
  ACCOUNT_LOCKED: 'Tài khoản đã bị khóa tạm thời, vui lòng thử lại sau',
  DUPLICATE_SKU: 'Mã SKU đã tồn tại',
  DUPLICATE_BARCODE: 'Mã vạch đã tồn tại',
  DUPLICATE_PHONE: 'Số điện thoại đã tồn tại',
  INSUFFICIENT_PAYMENT: 'Số tiền thanh toán không đủ',
  INVALID_REFRESH_TOKEN: 'Phiên đăng nhập hết hạn',
  REFRESH_TOKEN_REUSE_DETECTED: 'Phiên đăng nhập hết hạn',
  FORBIDDEN: 'Bạn không có quyền thực hiện thao tác này',
  NOT_FOUND: 'Không tìm thấy dữ liệu',
  VALIDATION_ERROR: 'Dữ liệu nhập không hợp lệ',
};

export function extractApiError(err: unknown): ApiErrorBody | null {
  if (!err) return null;
  const ax = err as AxiosError<{ error?: ApiErrorBody }>;
  const body = ax?.response?.data;
  if (body && typeof body === 'object' && 'error' in body && body.error) {
    const e = body.error as ApiErrorBody;
    if (e && typeof e.code === 'string') return e;
  }
  return null;
}

export function friendlyMessage(code: string, fallback?: string): string {
  return FRIENDLY[code] || fallback || 'Có lỗi xảy ra, vui lòng thử lại';
}

export function toFriendlyMessage(err: unknown, fallback?: string): string {
  const parsed = extractApiError(err);
  if (parsed) return friendlyMessage(parsed.code, parsed.message || fallback);
  if (err instanceof Error && err.message) return fallback || err.message;
  return fallback || 'Có lỗi xảy ra, vui lòng thử lại';
}
```

---

## Task 9: Layout, route guard, role gate, error boundary

**Files:**
- Create: `frontend/src/components/AppLayout.tsx`
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Create: `frontend/src/components/RoleGate.tsx`
- Create: `frontend/src/components/ErrorBoundary.tsx`

- [ ] Step 1: `ProtectedRoute.tsx`

```tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export default function ProtectedRoute() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (!accessToken) return <Navigate to="/login" replace />;
  return <Outlet />;
}
```

- [ ] Step 2: `RoleGate.tsx`

```tsx
import { ReactNode } from 'react';
import { useAuthStore, Role } from '../stores/authStore';

interface RoleGateProps {
  allow: Role[];
  fallback?: ReactNode;
  children: ReactNode;
}

export default function RoleGate({ allow, fallback = null, children }: RoleGateProps) {
  const role = useAuthStore((s) => s.user?.role);
  if (!role || !allow.includes(role)) return <>{fallback}</>;
  return <>{children}</>;
}
```

- [ ] Step 3: `AppLayout.tsx`

```tsx
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const navItems: Array<{ to: string; label: string }> = [
  { to: '/dashboard', label: 'Tổng quan' },
  { to: '/pos', label: 'Bán hàng (POS)' },
  { to: '/products', label: 'Sản phẩm' },
  { to: '/categories', label: 'Nhóm hàng' },
  { to: '/customers', label: 'Khách hàng' },
  { to: '/suppliers', label: 'Nhà cung cấp' },
  { to: '/inventory', label: 'Tồn kho' },
  { to: '/invoices', label: 'Hóa đơn' },
  { to: '/reports/revenue', label: 'Báo cáo' },
];

export default function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const tenant = useAuthStore((s) => s.tenant);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <aside className="w-60 shrink-0 bg-slate-900 text-slate-100 flex flex-col">
        <div className="px-4 py-4 text-lg font-semibold border-b border-slate-700">
          <Link to="/dashboard">my_kiot POS</Link>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm hover:bg-slate-800 ${isActive ? 'bg-slate-800 font-medium' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 px-4 flex items-center justify-between border-b border-slate-200 bg-white">
          <div className="text-sm text-slate-600">{tenant?.name ?? 'Chưa chọn shop'}</div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-700">{user?.full_name ?? 'Khách'}</span>
            <button
              onClick={handleLogout}
              className="px-3 py-1 rounded bg-slate-100 hover:bg-slate-200 border border-slate-200"
            >
              Đăng xuất
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

- [ ] Step 4: `ErrorBoundary.tsx`

```tsx
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props { children: ReactNode }
interface State { hasError: boolean; message?: string }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 text-center">
          <h1 className="text-xl font-semibold mb-2">Đã xảy ra lỗi</h1>
          <p className="text-slate-600">{this.state.message ?? 'Vui lòng tải lại trang'}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
```

---

## Task 10: Router (App.tsx) + main.tsx

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] Step 1: Replace `frontend/src/App.tsx`

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-2xl font-semibold">{title}</h1>;
}

function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm p-6 bg-white rounded shadow border border-slate-200">
        <h1 className="text-xl font-semibold mb-2">Đăng nhập</h1>
        <p className="text-sm text-slate-600">Form đăng nhập sẽ được triển khai ở Phase 1.</p>
      </div>
    </div>
  );
}

function RegisterPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-md p-6 bg-white rounded shadow border border-slate-200">
        <h1 className="text-xl font-semibold mb-2">Đăng ký shop</h1>
        <p className="text-sm text-slate-600">Form đăng ký sẽ được triển khai ở Phase 1.</p>
      </div>
    </div>
  );
}

function NotFound() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">404 — Không tìm thấy trang</h1>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Placeholder title="Tổng quan" />} />
              <Route path="/pos" element={<Placeholder title="Bán hàng (POS)" />} />
              <Route path="/products" element={<Placeholder title="Sản phẩm" />} />
              <Route path="/categories" element={<Placeholder title="Nhóm hàng" />} />
              <Route path="/customers" element={<Placeholder title="Khách hàng" />} />
              <Route path="/suppliers" element={<Placeholder title="Nhà cung cấp" />} />
              <Route path="/inventory" element={<Placeholder title="Tồn kho" />} />
              <Route path="/invoices" element={<Placeholder title="Hóa đơn" />} />
              <Route path="/reports/revenue" element={<Placeholder title="Báo cáo doanh thu" />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
```

- [ ] Step 2: Replace `frontend/src/main.tsx`

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

---

## Task 11: Smoke tests for format & errors

**Files:**
- Create: `frontend/src/utils/__tests__/format.test.ts`
- Create: `frontend/src/utils/__tests__/errors.test.ts`

- [ ] Step 1: `format.test.ts`

```ts
import { describe, it, expect } from 'vitest';
import { formatVND, formatDate, formatQty } from '../format';

describe('formatVND', () => {
  it('formats integer with vi-VN thousand separator', () => {
    expect(formatVND(1234567)).toBe('1.234.567 đ');
  });
  it('handles zero and null', () => {
    expect(formatVND(0)).toBe('0 đ');
    expect(formatVND(null)).toBe('0 đ');
    expect(formatVND(undefined)).toBe('0 đ');
  });
  it('accepts decimal string', () => {
    expect(formatVND('1500.50')).toBe('1.501 đ');
  });
  it('returns 0 đ for non-numeric', () => {
    expect(formatVND('abc')).toBe('0 đ');
  });
});

describe('formatQty', () => {
  it('trims trailing zeros', () => {
    expect(formatQty(1.5)).toBe('1.5');
    expect(formatQty(2)).toBe('2');
    expect(formatQty('0.300')).toBe('0.3');
  });
  it('handles null/empty', () => {
    expect(formatQty(null)).toBe('0');
    expect(formatQty('')).toBe('0');
  });
});

describe('formatDate', () => {
  it('formats ISO string to DD/MM/YYYY HH:mm', () => {
    const out = formatDate('2026-05-22T07:30:00Z');
    expect(out).toMatch(/^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}$/);
  });
  it('returns empty for null/invalid', () => {
    expect(formatDate(null)).toBe('');
    expect(formatDate('not-a-date')).toBe('');
  });
});
```

- [ ] Step 2: `errors.test.ts`

```ts
import { describe, it, expect } from 'vitest';
import { extractApiError, friendlyMessage, toFriendlyMessage } from '../errors';

describe('extractApiError', () => {
  it('parses axios-shaped error', () => {
    const err = {
      isAxiosError: true,
      response: { data: { error: { code: 'INSUFFICIENT_STOCK', message: 'X' } } },
    };
    const parsed = extractApiError(err);
    expect(parsed?.code).toBe('INSUFFICIENT_STOCK');
  });
  it('returns null for null / plain Error / unknown shapes', () => {
    expect(extractApiError(null)).toBeNull();
    expect(extractApiError(new Error('boom'))).toBeNull();
    expect(extractApiError({ response: { data: {} } })).toBeNull();
  });
});

describe('friendlyMessage', () => {
  it('maps known codes to Vietnamese', () => {
    expect(friendlyMessage('INSUFFICIENT_STOCK')).toBe('Số lượng tồn không đủ');
    expect(friendlyMessage('INVALID_CREDENTIALS')).toBe('Sai số điện thoại hoặc mật khẩu');
  });
  it('falls back to backend message then default', () => {
    expect(friendlyMessage('UNKNOWN_CODE', 'Custom')).toBe('Custom');
    expect(friendlyMessage('UNKNOWN_CODE')).toBe('Có lỗi xảy ra, vui lòng thử lại');
  });
});

describe('toFriendlyMessage', () => {
  it('uses extracted code mapping when available', () => {
    const err = {
      isAxiosError: true,
      response: { data: { error: { code: 'DUPLICATE_PHONE', message: 'dup' } } },
    };
    expect(toFriendlyMessage(err)).toBe('Số điện thoại đã tồn tại');
  });
  it('falls back to plain Error message', () => {
    expect(toFriendlyMessage(new Error('boom'))).toBe('boom');
  });
  it('uses fallback for unknown shapes', () => {
    expect(toFriendlyMessage({}, 'fb')).toBe('fb');
  });
});
```

---

## Task 12: Type-check & test run

- [ ] Step 1: Type-check
  Run: `cd frontend && npx tsc --noEmit`
  Expected: exit 0, no errors.

- [ ] Step 2: Run tests
  Run: `cd frontend && npm run test -- --run`
  Expected: all suites pass.

---
