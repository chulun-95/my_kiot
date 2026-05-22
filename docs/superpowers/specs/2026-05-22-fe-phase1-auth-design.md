# Phase 1 — Auth & Staff (Frontend Design)

Build_id: fe-build-2026-05-22 · Phase: 1 · Topic: auth · Date: 2026-05-22

## 1. Scope

Implement the authentication flow (register shop, login with lockout handling, refresh, logout, change-password, get-me) and staff management (list, create, update, deactivate, activate). UI text in Vietnamese. Stack: React 18 + TS + Tailwind + Zustand + react-router-dom + axios. Tests: Vitest + RTL + MSW.

Out of scope (deferred to later phases): forgot-password, OTP via SMS, multi-tenant tenant-switch UI (backend supports `requires_tenant_selection`; we will render a minimal "Select tenant" view inline within Login).

## 2. Routes

| Path | Layout | Auth | Notes |
|---|---|---|---|
| `/login` | unauth bare layout | none | If `accessToken` present → redirect to `/dashboard`. Handles tenant-selection step inline. |
| `/register` | unauth bare layout | none | Same redirect rule. After success, populate auth store + go to `/dashboard`. |
| `/me/change-password` | `AppLayout` | any role | Inside `ProtectedRoute`. After success, navigate to `/dashboard` and show toast (alert). |
| `/staff` | `AppLayout` | OWNER (via `RoleGate`) | List of staff with search, activate/deactivate actions, create + edit forms (modal). |

## 3. Components

### Auth pages

- **`src/pages/auth/Login.tsx`** — Form with fields: `phone`, `password`. On submit, POST `/auth/login`. If response is `LoginSuccess` → write to authStore + navigate. If response includes `requires_tenant_selection` → render tenant selector (radio list); on second submit include `tenant_id`. Handles 429 lockout (Vietnamese message), invalid credentials. Disables submit while pending.
- **`src/pages/auth/Register.tsx`** — Form: `shop_name`, `owner_name`, `phone`, `email` (optional), `password`. POST `/auth/register`. On 201, write auth store + navigate to `/dashboard`. Validates phone via simple regex `/^0\d{9}$/` client-side as soft check (server validates strictly).
- **`src/pages/auth/ChangePassword.tsx`** — Form: `current_password`, `new_password`, `confirm_password`. Client checks `new == confirm` and length ≥ 6. PUT `/auth/change-password`. On 200, server returns a fresh `TokenPair` — call `setAccessToken(newAccess)`. Show success message and navigate `/dashboard`.

### Staff pages

- **`src/pages/staff/StaffList.tsx`** — GET `/staff?page=&limit=&search=&is_active=` (OWNER only). Table columns: full_name, phone, email, role, is_active badge, last_login_at, actions. Search input (debounced 300ms via `setTimeout`). Pagination buttons. Buttons: "Thêm nhân viên" (opens create modal), per-row "Sửa", "Khóa" / "Mở khóa". Confirm-dialog (native `confirm`) before deactivate.
- **`src/pages/staff/StaffForm.tsx`** — Controlled form rendered inside a simple modal (`<div role="dialog">`). Supports two modes: `create` (full_name, phone, email, password) and `edit` (full_name, email; phone is immutable per backend `StaffUpdateRequest`). On submit, POST or PUT. On success, callback `onSaved()` so list re-fetches.

### Shared/utility additions (none new in components/) — uses existing `RoleGate`, `ProtectedRoute`, `AppLayout`, `errors.ts`.

## 4. API layer

### `src/api/auth.ts`

| Function | Method + URL | Request | Response |
|---|---|---|---|
| `register(payload)` | POST `/auth/register` | `{shop_name, owner_name, phone, email?, password}` | `{tenant, user, access_token, refresh_token}` |
| `login(payload)` | POST `/auth/login` | `{phone, password, tenant_id?}` | success: `{user, tenant, access_token, refresh_token}`. Or `{requires_tenant_selection: true, tenants: [...]}` |
| `logout(refreshToken)` | POST `/auth/logout` | `{refresh_token}` | `{message}` |
| `refresh(refreshToken)` | POST `/auth/refresh` | `{refresh_token}` | `LoginSuccess` shape |
| `me()` | GET `/auth/me` | — | `{user, tenant}` |
| `changePassword(payload)` | PUT `/auth/change-password` | `{current_password, new_password, confirm_password}` | `{access_token, refresh_token}` |

Note: the existing `src/api/client.ts` already handles 401 → refresh using HttpOnly cookie via `/auth/refresh` with empty body. Backend's refresh endpoint expects `{refresh_token}` in body. For Phase 1 we accept the cookie-driven scheme as a Phase 2 reality and keep refresh tokens in the in-memory store for explicit logout (per `LogoutRequest`). For login flow we store both tokens in memory (`authStore.refreshToken` added).

### `src/api/staff.ts`

| Function | Method + URL | Request | Response |
|---|---|---|---|
| `listStaff(params)` | GET `/staff` | query `page, limit, search, is_active` | `{items, pagination}` |
| `createStaff(payload)` | POST `/staff` | `{full_name, phone, email?, password}` | `StaffResponse` |
| `updateStaff(id, payload)` | PUT `/staff/{id}` | `{full_name?, email?}` | `StaffResponse` |
| `deactivateStaff(id)` | PATCH `/staff/{id}/deactivate` | — | `StaffResponse` |
| `activateStaff(id)` | PATCH `/staff/{id}/activate` | — | `StaffResponse` |

## 5. State (Zustand)

Extend `src/stores/authStore.ts`:

- Add `refreshToken: string | null` field.
- Add async actions:
  - `login(phone, password, tenantId?)` → call `api/auth.login`, on success write `user/tenant/access/refresh`; on tenant-selection return `{requires_tenant_selection: true, tenants}` for the caller component to render.
  - `register(payload)` → call `api/auth.register`, write all four.
  - `doLogout()` → if `refreshToken` present, call `api/auth.logout(refreshToken)`; always clear store.
- Existing `logout()` (synchronous) retained as a hard-clear used by 401 fallback in client.ts. `doLogout()` is the user-initiated version.
- Update `AppLayout` "Đăng xuất" to call `doLogout()`.

## 6. Edge cases & error handling

| Scenario | Handling |
|---|---|
| Login 401 / 400 with `INVALID_CREDENTIALS` | Show "Sai số điện thoại hoặc mật khẩu" via `toFriendlyMessage`. Stay on form. |
| Login 429 (rate-limit OR account lockout) | Show "Tài khoản đã bị khóa tạm thời, vui lòng thử lại sau". Disable submit 30s (UX nicety). |
| Register 409 `DUPLICATE_PHONE` | Show inline "Số điện thoại đã tồn tại". |
| ChangePassword mismatch (FE check) | Inline error "Mật khẩu xác nhận không khớp"; no API call. |
| Staff deactivate self | Backend returns 400 (we treat any non-2xx as toast error). |
| Refresh fails / expired | `client.ts` already redirects to `/login` and calls `logout()` in store. |
| Owner clicks "Thêm nhân viên" while CASHIER (shouldn't happen — route gated) | RoleGate hides the entire `/staff` page; layout sidebar shows "Nhân viên" link only for OWNER. |

## 7. Test plan

Vitest + RTL + MSW. Add MSW `setupServer` to `src/__tests__/setup.ts`. Extend `mocks/handlers.ts` with auth + staff endpoints.

| Test file | Behaviors |
|---|---|
| `src/api/__tests__/auth.test.ts` | login success, login 429 surfaces error, register success, me, changePassword |
| `src/stores/__tests__/authStore.test.ts` | initial state, login action sets user+tenant+tokens, doLogout clears, setUser updates only user |
| `src/pages/auth/__tests__/Login.test.tsx` | renders form (VN labels), submits with valid creds → calls login action, displays Vietnamese lockout message on 429 |
| `src/pages/auth/__tests__/Register.test.tsx` | renders form, submits, dispatches register action |
| `src/pages/staff/__tests__/StaffList.test.tsx` | renders staff rows, deactivate button triggers PATCH (handler asserts call), search filters; OWNER vs CASHIER gating via RoleGate is enforced upstream — here we test the page directly assuming role=OWNER |

Pass criteria: all new tests + 18 existing Phase 0 tests pass.

## 8. File list (Step 2 outputs)

Created:
- `frontend/src/api/auth.ts`
- `frontend/src/api/staff.ts`
- `frontend/src/api/__tests__/auth.test.ts`
- `frontend/src/pages/auth/Login.tsx`
- `frontend/src/pages/auth/Register.tsx`
- `frontend/src/pages/auth/ChangePassword.tsx`
- `frontend/src/pages/auth/__tests__/Login.test.tsx`
- `frontend/src/pages/auth/__tests__/Register.test.tsx`
- `frontend/src/pages/staff/StaffList.tsx`
- `frontend/src/pages/staff/StaffForm.tsx`
- `frontend/src/pages/staff/__tests__/StaffList.test.tsx`
- `frontend/src/stores/__tests__/authStore.test.ts`

Modified:
- `frontend/src/App.tsx` (wire routes)
- `frontend/src/stores/authStore.ts` (add `refreshToken`, async actions)
- `frontend/src/components/AppLayout.tsx` (add "Nhân viên" link gated by OWNER, swap logout to `doLogout`)
- `frontend/src/__tests__/setup.ts` (MSW server lifecycle)
- `frontend/src/__tests__/mocks/handlers.ts` (extend with auth + staff)
