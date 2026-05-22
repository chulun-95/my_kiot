# FE Phase 0 — Setup khung FE (Design)

> Foundation phase. No business endpoints. Goal: a working Vite + React + TS + Tailwind app skeleton with axios client (JWT refresh), Zustand auth store, layout shell, route protection, format/error utilities, Vitest+MSW test harness, and smoke tests.

## 1. Scope

This phase produces a buildable, test-runnable `frontend/` project. It does NOT implement any business pages — placeholders only. Later phases (1-6) extend this skeleton.

## 2. Routes (placeholder router)

| Path | Element | Notes |
|---|---|---|
| `/login` | `<LoginPage/>` (placeholder) | public |
| `/register` | `<RegisterPage/>` (placeholder) | public |
| `/` | `<AppLayout/>` with `<ProtectedRoute/>` wrap | requires auth |
| `/dashboard` | `<DashboardPlaceholder/>` | index inside AppLayout |
| `/products`, `/customers`, `/suppliers`, `/categories`, `/inventory`, `/pos`, `/invoices`, `/reports/revenue` | `<Placeholder/>` | each renders a single h1 in Vietnamese |
| `*` | `<NotFound/>` | basic 404 |

All placeholders are inline components (no separate pages directory yet — Phase 1+ creates real pages).

## 3. Components

- **`src/components/AppLayout.tsx`** — Sidebar (logo + nav links: Dashboard, Sản phẩm, Khách hàng, NCC, Nhập kho, Tồn kho, POS, Hóa đơn, Báo cáo) + topbar (tenant name, user name, logout button) + `<Outlet/>` main area. Reads from authStore. Tailwind layout: `flex h-screen`, sidebar `w-60`, main `flex-1 overflow-auto`.
- **`src/components/ProtectedRoute.tsx`** — Reads `accessToken` from authStore. If null → `<Navigate to="/login" replace/>`. Else `<Outlet/>`.
- **`src/components/RoleGate.tsx`** — Props: `allow: Role[]`, `children: ReactNode`, optional `fallback`. Reads `user.role` from authStore; if not in allow list, renders fallback (default: nothing). Used by later phases (e.g., Owner-only menu items, cancel buttons).
- **`src/components/ErrorBoundary.tsx`** — (light version, full version in Phase 6) basic class component to catch render errors.

## 4. State (Zustand)

### `src/stores/authStore.ts`

Shape:
```ts
interface AuthState {
  user: User | null;          // { id, full_name, role, phone?, email? }
  tenant: Tenant | null;      // { id, name, slug }
  accessToken: string | null; // in-memory ONLY (XSS hardening per CLAUDE.md)
  setAuth(payload: { user; tenant; accessToken }): void;
  setUser(user: User): void;
  setAccessToken(token: string | null): void;
  logout(): void;
}
```

Persistence: **none in-memory only** (refresh token is httpOnly cookie handled by browser). On hard refresh, FE calls `/auth/refresh` via interceptor → if 401 → redirect login.

## 5. API client

### `src/api/client.ts`

- `axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1', withCredentials: true, headers: { 'X-Requested-With': 'XMLHttpRequest' } })`
- Request interceptor: attach `Authorization: Bearer ${accessToken}` from authStore if present.
- Response interceptor: on 401 with code `TOKEN_EXPIRED` (or generic 401), call `/auth/refresh`. If refresh succeeds → store new accessToken → retry original request. If refresh fails → `authStore.logout()` + window.location = `/login`.
- Single-flight refresh: a module-level `refreshPromise` ensures concurrent 401s share one refresh call (prevents thundering herd).

## 6. API mapping

| Endpoint | Caller | Request | Response handling |
|---|---|---|---|
| `POST /auth/refresh` | client.ts interceptor | empty body, relies on httpOnly cookie | sets new accessToken via authStore.setAccessToken |

No other endpoints in this phase.

## 7. Utilities

### `src/utils/format.ts`

- `formatVND(amount: number | string): string` — `"1.234.567 đ"`. Uses `Intl.NumberFormat('vi-VN')`. Accepts string (DECIMAL serialized) by parseFloat.
- `formatDate(iso: string | Date, fmt?: string): string` — Default `DD/MM/YYYY HH:mm`. Uses dayjs with `Asia/Ho_Chi_Minh` timezone via dayjs/plugin/timezone + utc. Falls back to native if dayjs fails.
- `formatQty(qty: number | string): string` — trims trailing zeros: `1.5`, `2`, `0.3`. Up to 3 decimal places.

### `src/utils/errors.ts`

Backend error shape: `{ error: { code: string; message: string; details?: any } }`.

- `extractApiError(err: unknown): { code: string; message: string; details?: any } | null` — accepts axios error, returns parsed error or null.
- `friendlyMessage(code: string, fallback?: string): string` — maps known codes to Vietnamese:
  - `INSUFFICIENT_STOCK` → "Số lượng tồn không đủ"
  - `INVALID_CREDENTIALS` → "Sai số điện thoại hoặc mật khẩu"
  - `ACCOUNT_LOCKED` → "Tài khoản đã bị khóa tạm thời, vui lòng thử lại sau"
  - `DUPLICATE_SKU` → "Mã SKU đã tồn tại"
  - `DUPLICATE_BARCODE` → "Mã vạch đã tồn tại"
  - `DUPLICATE_PHONE` → "Số điện thoại đã tồn tại"
  - `INSUFFICIENT_PAYMENT` → "Số tiền thanh toán không đủ"
  - `INVALID_REFRESH_TOKEN`, `REFRESH_TOKEN_REUSE_DETECTED` → "Phiên đăng nhập hết hạn"
  - `FORBIDDEN` → "Bạn không có quyền thực hiện thao tác này"
  - `NOT_FOUND` → "Không tìm thấy dữ liệu"
  - `VALIDATION_ERROR` → "Dữ liệu nhập không hợp lệ"
  - default → backend message or fallback or "Có lỗi xảy ra, vui lòng thử lại"
- `toFriendlyMessage(err: unknown): string` — convenience combining extract + friendly.

## 8. Edge cases & error handling

- **No backend during dev:** axios interceptors must not crash on undefined responses; refresh handler tolerates network errors.
- **Concurrent 401s:** single-flight refresh promise.
- **Refresh during refresh:** if refresh itself returns 401 → immediate logout.
- **Logout from any tab:** Phase 0 doesn't implement cross-tab sync; deferred.
- **Empty accessToken on first load:** ProtectedRoute redirects to /login. Optional bootstrap call to `/auth/refresh` on app mount happens in Phase 1 (auth bootstrap); Phase 0 keeps it minimal — user must log in.
- **Tailwind purge:** content globs cover `src/**/*.{ts,tsx,html}`.

## 9. File layout produced

```
frontend/
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── vitest.config.ts
├── tailwind.config.js
├── postcss.config.js
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── vite-env.d.ts
│   ├── api/
│   │   └── client.ts
│   ├── stores/
│   │   └── authStore.ts
│   ├── components/
│   │   ├── AppLayout.tsx
│   │   ├── ProtectedRoute.tsx
│   │   ├── RoleGate.tsx
│   │   └── ErrorBoundary.tsx
│   ├── utils/
│   │   ├── format.ts
│   │   ├── errors.ts
│   │   └── __tests__/
│   │       ├── format.test.ts
│   │       └── errors.test.ts
│   └── __tests__/
│       ├── setup.ts
│       └── mocks/
│           └── handlers.ts
```

## 10. Test plan (Phase 0 smoke)

- **`format.test.ts`** — formatVND on integers / decimal strings / zero; formatQty trims; formatDate returns DD/MM/YYYY HH:mm for ISO input.
- **`errors.test.ts`** — extractApiError on axios-shaped error, on null, on plain Error; friendlyMessage maps known codes, falls back to backend message, falls back to default.

Run via `npm run test -- --run`. Expected: all pass.

## 11. Out of scope (Phase 1+)

- Real login/register forms (Phase 1)
- Auth bootstrap on app mount (Phase 1)
- Toast notification system (Phase 1 — likely react-hot-toast or custom)
- Cross-tab logout sync (Phase 6)
- Full ErrorBoundary with reset (Phase 6)
- PWA manifest (Phase 6)
