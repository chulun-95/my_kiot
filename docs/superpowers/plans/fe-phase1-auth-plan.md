# FE Phase 1 — Auth & Staff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Vietnamese-language authentication (register, login w/ lockout, refresh, logout, change-password, me) and OWNER-only staff management (list, create, update, deactivate, activate) on top of the Phase 0 scaffolding.

**Architecture:** Pages under `frontend/src/pages/{auth,staff}`. Thin per-domain API modules under `frontend/src/api/{auth,staff}.ts` calling the existing axios `apiClient`. Zustand `authStore` extended with `refreshToken` and async `login/register/doLogout` actions. Routes wired in `App.tsx`; OWNER-only routes protected via existing `RoleGate`. Tests use Vitest + RTL + MSW.

**Tech Stack:** React 18 + TS, Tailwind, Zustand, react-router-dom v7, axios, Vitest, RTL, MSW.

---

## File Structure

Created:
- `frontend/src/api/auth.ts` — auth endpoints (register, login, refresh, logout, me, changePassword)
- `frontend/src/api/staff.ts` — staff endpoints (list, create, update, deactivate, activate)
- `frontend/src/pages/auth/Login.tsx`
- `frontend/src/pages/auth/Register.tsx`
- `frontend/src/pages/auth/ChangePassword.tsx`
- `frontend/src/pages/staff/StaffList.tsx`
- `frontend/src/pages/staff/StaffForm.tsx`
- `frontend/src/api/__tests__/auth.test.ts`
- `frontend/src/stores/__tests__/authStore.test.ts`
- `frontend/src/pages/auth/__tests__/Login.test.tsx`
- `frontend/src/pages/auth/__tests__/Register.test.tsx`
- `frontend/src/pages/staff/__tests__/StaffList.test.tsx`

Modified:
- `frontend/src/stores/authStore.ts` — add `refreshToken`, async actions
- `frontend/src/App.tsx` — wire new routes
- `frontend/src/components/AppLayout.tsx` — add OWNER-only "Nhân viên" link, call `doLogout`
- `frontend/src/__tests__/setup.ts` — MSW server lifecycle
- `frontend/src/__tests__/mocks/handlers.ts` — extend with auth + staff handlers

---

### Task 1: Extend authStore with tokens + async actions

**Files:**
- Modify: `frontend/src/stores/authStore.ts`

- [ ] **Step 1: Update store**

```typescript
import { create } from 'zustand';
import * as authApi from '../api/auth';

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

export interface TenantOption {
  id: number;
  name: string;
  role: Role;
}

export interface LoginPendingSelection {
  requires_tenant_selection: true;
  tenants: TenantOption[];
}

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  accessToken: string | null;
  refreshToken: string | null;
  setAuth: (payload: { user: User; tenant: Tenant; accessToken: string; refreshToken: string }) => void;
  setUser: (user: User) => void;
  setAccessToken: (token: string | null) => void;
  logout: () => void;
  login: (phone: string, password: string, tenantId?: number) => Promise<LoginPendingSelection | null>;
  register: (payload: authApi.RegisterPayload) => Promise<void>;
  doLogout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  tenant: null,
  accessToken: null,
  refreshToken: null,
  setAuth: ({ user, tenant, accessToken, refreshToken }) =>
    set({ user, tenant, accessToken, refreshToken }),
  setUser: (user) => set({ user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  logout: () => set({ user: null, tenant: null, accessToken: null, refreshToken: null }),
  login: async (phone, password, tenantId) => {
    const res = await authApi.login({ phone, password, tenant_id: tenantId });
    if ('requires_tenant_selection' in res && res.requires_tenant_selection) {
      return res;
    }
    set({
      user: res.user,
      tenant: res.tenant,
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
    });
    return null;
  },
  register: async (payload) => {
    const res = await authApi.register(payload);
    set({
      user: res.user,
      tenant: res.tenant,
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
    });
  },
  doLogout: async () => {
    const rt = get().refreshToken;
    if (rt) {
      try {
        await authApi.logout(rt);
      } catch {
        // swallow — always clear local state
      }
    }
    set({ user: null, tenant: null, accessToken: null, refreshToken: null });
  },
}));
```

- [ ] **Step 2: Verify tsc**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (after Task 2 lands; auth.ts types are referenced).

---

### Task 2: Create `src/api/auth.ts`

**Files:**
- Create: `frontend/src/api/auth.ts`

- [ ] **Step 1: Implement**

```typescript
import apiClient from './client';
import type { Role, Tenant, User, TenantOption, LoginPendingSelection } from '../stores/authStore';

export interface RegisterPayload {
  shop_name: string;
  owner_name: string;
  phone: string;
  email?: string;
  password: string;
}

export interface LoginPayload {
  phone: string;
  password: string;
  tenant_id?: number;
}

export interface LoginSuccess {
  user: User;
  tenant: Tenant;
  access_token: string;
  refresh_token: string;
}

export interface AuthSuccess extends LoginSuccess {}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface MeResponse {
  user: User;
  tenant: Tenant;
}

export async function register(payload: RegisterPayload): Promise<AuthSuccess> {
  const { data } = await apiClient.post<AuthSuccess>('/auth/register', payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<LoginSuccess | LoginPendingSelection> {
  const { data } = await apiClient.post<LoginSuccess | LoginPendingSelection>('/auth/login', payload);
  return data;
}

export async function refresh(refreshToken: string): Promise<LoginSuccess> {
  const { data } = await apiClient.post<LoginSuccess>('/auth/refresh', { refresh_token: refreshToken });
  return data;
}

export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post('/auth/logout', { refresh_token: refreshToken });
}

export async function me(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>('/auth/me');
  return data;
}

export async function changePassword(payload: ChangePasswordPayload): Promise<TokenPair> {
  const { data } = await apiClient.put<TokenPair>('/auth/change-password', payload);
  return data;
}

// Re-export types referenced by store
export type { Role, User, Tenant, TenantOption };
```

---

### Task 3: Create `src/api/staff.ts`

**Files:**
- Create: `frontend/src/api/staff.ts`

- [ ] **Step 1: Implement**

```typescript
import apiClient from './client';
import type { Role } from '../stores/authStore';

export interface StaffResponse {
  id: number;
  full_name: string;
  phone: string | null;
  email: string | null;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface StaffListResponse {
  items: StaffResponse[];
  pagination: Pagination;
}

export interface ListParams {
  page?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
}

export interface StaffCreatePayload {
  full_name: string;
  phone: string;
  email?: string;
  password: string;
}

export interface StaffUpdatePayload {
  full_name?: string;
  email?: string;
}

export async function listStaff(params: ListParams = {}): Promise<StaffListResponse> {
  const { data } = await apiClient.get<StaffListResponse>('/staff', { params });
  return data;
}

export async function createStaff(payload: StaffCreatePayload): Promise<StaffResponse> {
  const { data } = await apiClient.post<StaffResponse>('/staff', payload);
  return data;
}

export async function updateStaff(id: number, payload: StaffUpdatePayload): Promise<StaffResponse> {
  const { data } = await apiClient.put<StaffResponse>(`/staff/${id}`, payload);
  return data;
}

export async function deactivateStaff(id: number): Promise<StaffResponse> {
  const { data } = await apiClient.patch<StaffResponse>(`/staff/${id}/deactivate`);
  return data;
}

export async function activateStaff(id: number): Promise<StaffResponse> {
  const { data } = await apiClient.patch<StaffResponse>(`/staff/${id}/activate`);
  return data;
}
```

---

### Task 4: Implement `Login.tsx`

**Files:**
- Create: `frontend/src/pages/auth/Login.tsx`

- [ ] **Step 1: Implement**

```tsx
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import type { TenantOption } from '../../stores/authStore';
import { toFriendlyMessage, extractApiError } from '../../utils/errors';

export default function Login() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [tenants, setTenants] = useState<TenantOption[] | null>(null);
  const [tenantId, setTenantId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(phone, password, tenantId ?? undefined);
      if (result && result.requires_tenant_selection) {
        setTenants(result.tenants);
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      const api = extractApiError(err);
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 429 || api?.code === 'ACCOUNT_LOCKED') {
        setError('Tài khoản đã bị khóa tạm thời, vui lòng thử lại sau');
      } else {
        setError(toFriendlyMessage(err, 'Sai số điện thoại hoặc mật khẩu'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm p-6 bg-white rounded shadow border border-slate-200 space-y-4"
      >
        <h1 className="text-xl font-semibold">Đăng nhập</h1>

        <label className="block">
          <span className="text-sm text-slate-700">Số điện thoại</span>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
            autoFocus
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Mật khẩu</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        {tenants && tenants.length > 0 && (
          <fieldset className="space-y-2">
            <legend className="text-sm text-slate-700">Chọn shop</legend>
            {tenants.map((t) => (
              <label key={t.id} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="tenant"
                  value={t.id}
                  checked={tenantId === t.id}
                  onChange={() => setTenantId(t.id)}
                />
                {t.name} <span className="text-slate-500">({t.role})</span>
              </label>
            ))}
          </fieldset>
        )}

        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang xử lý...' : 'Đăng nhập'}
        </button>

        <div className="text-sm text-slate-600">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="text-slate-900 underline">
            Đăng ký shop mới
          </Link>
        </div>
      </form>
    </div>
  );
}
```

---

### Task 5: Implement `Register.tsx`

**Files:**
- Create: `frontend/src/pages/auth/Register.tsx`

- [ ] **Step 1: Implement**

```tsx
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { toFriendlyMessage } from '../../utils/errors';

export default function Register() {
  const navigate = useNavigate();
  const register = useAuthStore((s) => s.register);
  const [shopName, setShopName] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!/^0\d{9}$/.test(phone)) {
      setError('Số điện thoại phải có 10 chữ số, bắt đầu bằng 0');
      return;
    }
    setSubmitting(true);
    try {
      await register({
        shop_name: shopName,
        owner_name: ownerName,
        phone,
        email: email || undefined,
        password,
      });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md p-6 bg-white rounded shadow border border-slate-200 space-y-4"
      >
        <h1 className="text-xl font-semibold">Đăng ký shop mới</h1>

        <label className="block">
          <span className="text-sm text-slate-700">Tên shop</span>
          <input
            value={shopName}
            onChange={(e) => setShopName(e.target.value)}
            required
            minLength={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Tên chủ shop</span>
          <input
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
            required
            minLength={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Số điện thoại</span>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Email (tùy chọn)</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        <label className="block">
          <span className="text-sm text-slate-700">Mật khẩu</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>

        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang xử lý...' : 'Đăng ký'}
        </button>

        <div className="text-sm text-slate-600">
          Đã có tài khoản?{' '}
          <Link to="/login" className="text-slate-900 underline">
            Đăng nhập
          </Link>
        </div>
      </form>
    </div>
  );
}
```

---

### Task 6: Implement `ChangePassword.tsx`

**Files:**
- Create: `frontend/src/pages/auth/ChangePassword.tsx`

- [ ] **Step 1: Implement**

```tsx
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { changePassword } from '../../api/auth';
import { toFriendlyMessage } from '../../utils/errors';

export default function ChangePassword() {
  const navigate = useNavigate();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp');
      return;
    }
    if (newPassword.length < 6) {
      setError('Mật khẩu mới phải có ít nhất 6 ký tự');
      return;
    }
    setSubmitting(true);
    try {
      const pair = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setAccessToken(pair.access_token);
      setSuccess('Đổi mật khẩu thành công');
      setTimeout(() => navigate('/dashboard'), 800);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md">
      <h1 className="text-2xl font-semibold mb-4">Đổi mật khẩu</h1>
      <form onSubmit={onSubmit} className="space-y-4 bg-white p-4 rounded border border-slate-200">
        <label className="block">
          <span className="text-sm text-slate-700">Mật khẩu hiện tại</span>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Mật khẩu mới</span>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Xác nhận mật khẩu</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}
        {success && (
          <div role="status" className="text-sm text-emerald-600">
            {success}
          </div>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
        >
          {submitting ? 'Đang lưu...' : 'Lưu'}
        </button>
      </form>
    </div>
  );
}
```

---

### Task 7: Implement `StaffForm.tsx` (modal)

**Files:**
- Create: `frontend/src/pages/staff/StaffForm.tsx`

- [ ] **Step 1: Implement**

```tsx
import { useState, type FormEvent } from 'react';
import * as staffApi from '../../api/staff';
import type { StaffResponse } from '../../api/staff';
import { toFriendlyMessage } from '../../utils/errors';

interface Props {
  mode: 'create' | 'edit';
  initial?: StaffResponse;
  onClose: () => void;
  onSaved: () => void;
}

export default function StaffForm({ mode, initial, onClose, onSaved }: Props) {
  const [fullName, setFullName] = useState(initial?.full_name ?? '');
  const [phone, setPhone] = useState(initial?.phone ?? '');
  const [email, setEmail] = useState(initial?.email ?? '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'create') {
        await staffApi.createStaff({
          full_name: fullName,
          phone,
          email: email || undefined,
          password,
        });
      } else if (initial) {
        await staffApi.updateStaff(initial.id, {
          full_name: fullName,
          email: email || undefined,
        });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50"
    >
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-white p-5 rounded shadow space-y-3"
      >
        <h2 className="text-lg font-semibold">
          {mode === 'create' ? 'Thêm nhân viên' : 'Sửa nhân viên'}
        </h2>
        <label className="block">
          <span className="text-sm text-slate-700">Họ tên</span>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            minLength={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Số điện thoại</span>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required={mode === 'create'}
            disabled={mode === 'edit'}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded disabled:bg-slate-100"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Email (tùy chọn)</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        {mode === 'create' && (
          <label className="block">
            <span className="text-sm text-slate-700">Mật khẩu khởi tạo</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            />
          </label>
        )}
        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 rounded border border-slate-300"
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
          >
            {submitting ? 'Đang lưu...' : 'Lưu'}
          </button>
        </div>
      </form>
    </div>
  );
}
```

---

### Task 8: Implement `StaffList.tsx`

**Files:**
- Create: `frontend/src/pages/staff/StaffList.tsx`

- [ ] **Step 1: Implement**

```tsx
import { useCallback, useEffect, useState } from 'react';
import * as staffApi from '../../api/staff';
import type { Pagination, StaffResponse } from '../../api/staff';
import StaffForm from './StaffForm';
import { toFriendlyMessage } from '../../utils/errors';

export default function StaffList() {
  const [items, setItems] = useState<StaffResponse[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
  });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<
    { mode: 'create' } | { mode: 'edit'; staff: StaffResponse } | null
  >(null);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await staffApi.listStaff({
        page,
        limit: 20,
        search: search || undefined,
      });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    const handle = setTimeout(load, 300);
    return () => clearTimeout(handle);
  }, [load]);

  const handleDeactivate = async (staff: StaffResponse) => {
    if (!confirm(`Khóa tài khoản ${staff.full_name}?`)) return;
    try {
      await staffApi.deactivateStaff(staff.id);
      load();
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  const handleActivate = async (staff: StaffResponse) => {
    try {
      await staffApi.activateStaff(staff.id);
      load();
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Nhân viên</h1>
        <button
          onClick={() => setModal({ mode: 'create' })}
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          Thêm nhân viên
        </button>
      </div>

      <input
        type="search"
        placeholder="Tìm theo tên hoặc SĐT..."
        value={search}
        onChange={(e) => {
          setPage(1);
          setSearch(e.target.value);
        }}
        className="w-full max-w-sm px-3 py-2 border border-slate-300 rounded"
      />

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">Họ tên</th>
              <th className="px-3 py-2 text-left">SĐT</th>
              <th className="px-3 py-2 text-left">Email</th>
              <th className="px-3 py-2 text-left">Vai trò</th>
              <th className="px-3 py-2 text-left">Trạng thái</th>
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Đang tải...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Chưa có nhân viên
                </td>
              </tr>
            ) : (
              items.map((s) => (
                <tr key={s.id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{s.full_name}</td>
                  <td className="px-3 py-2">{s.phone ?? '-'}</td>
                  <td className="px-3 py-2">{s.email ?? '-'}</td>
                  <td className="px-3 py-2">{s.role}</td>
                  <td className="px-3 py-2">
                    {s.is_active ? (
                      <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
                        Đang hoạt động
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                        Đã khóa
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right space-x-2">
                    <button
                      onClick={() => setModal({ mode: 'edit', staff: s })}
                      className="px-2 py-1 rounded border border-slate-300"
                    >
                      Sửa
                    </button>
                    {s.is_active ? (
                      <button
                        onClick={() => handleDeactivate(s)}
                        className="px-2 py-1 rounded border border-rose-300 text-rose-700"
                      >
                        Khóa
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivate(s)}
                        className="px-2 py-1 rounded border border-emerald-300 text-emerald-700"
                      >
                        Mở khóa
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">
          Trang {pagination.page} / {Math.max(1, pagination.total_pages)} — {pagination.total} nhân viên
        </span>
        <div className="space-x-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Trước
          </button>
          <button
            disabled={page >= pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Sau
          </button>
        </div>
      </div>

      {modal && (
        <StaffForm
          mode={modal.mode}
          initial={modal.mode === 'edit' ? modal.staff : undefined}
          onClose={() => setModal(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
```

---

### Task 9: Wire routes in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace placeholders for /login, /register; add /me/change-password and /staff**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import RoleGate from './components/RoleGate';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ChangePassword from './pages/auth/ChangePassword';
import StaffList from './pages/staff/StaffList';

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-2xl font-semibold">{title}</h1>;
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
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
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
              <Route path="/me/change-password" element={<ChangePassword />} />
              <Route
                path="/staff"
                element={
                  <RoleGate
                    allow={['OWNER']}
                    fallback={<h1 className="text-2xl font-semibold">Không có quyền truy cập</h1>}
                  >
                    <StaffList />
                  </RoleGate>
                }
              />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
```

---

### Task 10: Update `AppLayout` (OWNER-only staff link + doLogout)

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: Show "Nhân viên" link only for OWNER; use `doLogout`**

```tsx
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const baseNav: Array<{ to: string; label: string }> = [
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
  const doLogout = useAuthStore((s) => s.doLogout);
  const navigate = useNavigate();

  const navItems =
    user?.role === 'OWNER'
      ? [...baseNav, { to: '/staff', label: 'Nhân viên' }]
      : baseNav;

  const handleLogout = async () => {
    await doLogout();
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
            <Link to="/me/change-password" className="text-slate-700 underline">
              Đổi mật khẩu
            </Link>
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

- [ ] **Step 2: Run tsc**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS

---

### Task 11: Extend MSW handlers & setup

**Files:**
- Modify: `frontend/src/__tests__/setup.ts`
- Modify: `frontend/src/__tests__/mocks/handlers.ts`

- [ ] **Step 1: Add MSW server lifecycle to setup**

```typescript
import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from './mocks/handlers';

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

- [ ] **Step 2: Extend handlers**

```typescript
import { http, HttpResponse } from 'msw';

interface RegisterBody {
  shop_name: string;
  owner_name: string;
  phone: string;
  email?: string;
  password: string;
}

interface LoginBody {
  phone: string;
  password: string;
  tenant_id?: number;
}

const successUser = {
  id: 1,
  full_name: 'Chủ shop',
  phone: '0900000001',
  email: null,
  role: 'OWNER' as const,
};

const successTenant = { id: 1, name: 'Shop A', slug: 'shop-a' };

const tokens = {
  access_token: 'access-1',
  refresh_token: 'refresh-1',
  token_type: 'Bearer',
};

export const handlers = [
  http.post('*/auth/refresh', () => HttpResponse.json({ access_token: 'mock-access-token' })),
  http.post('*/auth/register', async ({ request }) => {
    const body = (await request.json()) as RegisterBody;
    if (body.phone === '0911111111') {
      return HttpResponse.json(
        { error: { code: 'DUPLICATE_PHONE', message: 'Số điện thoại đã tồn tại' } },
        { status: 409 },
      );
    }
    return HttpResponse.json(
      { user: successUser, tenant: successTenant, ...tokens },
      { status: 201 },
    );
  }),
  http.post('*/auth/login', async ({ request }) => {
    const body = (await request.json()) as LoginBody;
    if (body.password === 'locked') {
      return HttpResponse.json(
        { error: { code: 'ACCOUNT_LOCKED', message: 'Bị khóa' } },
        { status: 429 },
      );
    }
    if (body.password === 'wrong') {
      return HttpResponse.json(
        { error: { code: 'INVALID_CREDENTIALS', message: 'Sai' } },
        { status: 401 },
      );
    }
    return HttpResponse.json({ user: successUser, tenant: successTenant, ...tokens });
  }),
  http.post('*/auth/logout', () => HttpResponse.json({ message: 'ok' })),
  http.get('*/auth/me', () => HttpResponse.json({ user: successUser, tenant: successTenant })),
  http.put('*/auth/change-password', () =>
    HttpResponse.json({ access_token: 'new-access', refresh_token: 'new-refresh' }),
  ),
  http.get('*/staff', () =>
    HttpResponse.json({
      items: [
        {
          id: 2,
          full_name: 'Nhân viên A',
          phone: '0900000002',
          email: null,
          role: 'CASHIER',
          is_active: true,
          last_login_at: null,
          created_at: '2026-05-22T00:00:00Z',
        },
      ],
      pagination: { page: 1, limit: 20, total: 1, total_pages: 1 },
    }),
  ),
  http.post('*/staff', async ({ request }) => {
    const body = (await request.json()) as { full_name: string; phone: string };
    return HttpResponse.json(
      {
        id: 99,
        full_name: body.full_name,
        phone: body.phone,
        email: null,
        role: 'CASHIER',
        is_active: true,
        last_login_at: null,
        created_at: '2026-05-22T00:00:00Z',
      },
      { status: 201 },
    );
  }),
  http.put('*/staff/:id', async ({ request, params }) => {
    const body = (await request.json()) as { full_name?: string };
    return HttpResponse.json({
      id: Number(params.id),
      full_name: body.full_name ?? 'Nhân viên',
      phone: '0900000002',
      email: null,
      role: 'CASHIER',
      is_active: true,
      last_login_at: null,
      created_at: '2026-05-22T00:00:00Z',
    });
  }),
  http.patch('*/staff/:id/deactivate', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      full_name: 'Nhân viên A',
      phone: '0900000002',
      email: null,
      role: 'CASHIER',
      is_active: false,
      last_login_at: null,
      created_at: '2026-05-22T00:00:00Z',
    }),
  ),
  http.patch('*/staff/:id/activate', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      full_name: 'Nhân viên A',
      phone: '0900000002',
      email: null,
      role: 'CASHIER',
      is_active: true,
      last_login_at: null,
      created_at: '2026-05-22T00:00:00Z',
    }),
  ),
];
```

---

### Task 12: Test — `authStore.test.ts`

**Files:**
- Create: `frontend/src/stores/__tests__/authStore.test.ts`

- [ ] **Step 1: Write tests**

```typescript
import { beforeEach, describe, expect, it } from 'vitest';
import { useAuthStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, tenant: null, accessToken: null, refreshToken: null });
  });

  it('starts empty', () => {
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.tenant).toBeNull();
    expect(s.accessToken).toBeNull();
    expect(s.refreshToken).toBeNull();
  });

  it('login action sets user/tenant/tokens via API', async () => {
    const res = await useAuthStore.getState().login('0900000001', 'secret123');
    expect(res).toBeNull();
    const s = useAuthStore.getState();
    expect(s.user?.id).toBe(1);
    expect(s.tenant?.slug).toBe('shop-a');
    expect(s.accessToken).toBe('access-1');
    expect(s.refreshToken).toBe('refresh-1');
  });

  it('doLogout clears state', async () => {
    useAuthStore.setState({
      user: { id: 1, full_name: 'X', role: 'OWNER' },
      tenant: { id: 1, name: 'Y', slug: 'y' },
      accessToken: 'a',
      refreshToken: 'r',
    });
    await useAuthStore.getState().doLogout();
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.accessToken).toBeNull();
    expect(s.refreshToken).toBeNull();
  });

  it('setUser updates only user', () => {
    useAuthStore.setState({ accessToken: 'a' });
    useAuthStore.getState().setUser({ id: 2, full_name: 'Z', role: 'CASHIER' });
    const s = useAuthStore.getState();
    expect(s.user?.id).toBe(2);
    expect(s.accessToken).toBe('a');
  });
});
```

---

### Task 13: Test — `api/__tests__/auth.test.ts`

**Files:**
- Create: `frontend/src/api/__tests__/auth.test.ts`

- [ ] **Step 1: Write tests**

```typescript
import { describe, it, expect } from 'vitest';
import * as authApi from '../auth';

describe('auth API', () => {
  it('login returns user/tenant/tokens', async () => {
    const res = await authApi.login({ phone: '0900000001', password: 'good' });
    expect('user' in res).toBe(true);
    if ('user' in res) {
      expect(res.user.id).toBe(1);
      expect(res.tenant.slug).toBe('shop-a');
    }
  });

  it('login surfaces 429 lockout as axios error', async () => {
    await expect(authApi.login({ phone: '0900000001', password: 'locked' })).rejects.toMatchObject({
      response: { status: 429 },
    });
  });

  it('register returns auth payload', async () => {
    const res = await authApi.register({
      shop_name: 'S',
      owner_name: 'O',
      phone: '0922222222',
      password: 'secret1',
    });
    expect(res.access_token).toBe('access-1');
  });

  it('me returns user + tenant', async () => {
    const res = await authApi.me();
    expect(res.user.id).toBe(1);
  });

  it('changePassword returns new token pair', async () => {
    const res = await authApi.changePassword({
      current_password: 'old',
      new_password: 'newsecret',
      confirm_password: 'newsecret',
    });
    expect(res.access_token).toBe('new-access');
  });
});
```

---

### Task 14: Test — `Login.test.tsx`

**Files:**
- Create: `frontend/src/pages/auth/__tests__/Login.test.tsx`

- [ ] **Step 1: Write tests**

```tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Login from '../Login';
import { useAuthStore } from '../../../stores/authStore';

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

describe('Login page', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, tenant: null, accessToken: null, refreshToken: null });
  });

  it('renders Vietnamese form labels', () => {
    renderLogin();
    expect(screen.getByText('Đăng nhập')).toBeInTheDocument();
    expect(screen.getByText('Số điện thoại')).toBeInTheDocument();
    expect(screen.getByText('Mật khẩu')).toBeInTheDocument();
  });

  it('submits valid credentials and updates auth store', async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText('Số điện thoại'), {
      target: { value: '0900000001' },
    });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'good123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));
    await waitFor(() => {
      expect(useAuthStore.getState().accessToken).toBe('access-1');
    });
  });

  it('shows Vietnamese lockout message on 429', async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText('Số điện thoại'), {
      target: { value: '0900000001' },
    });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), {
      target: { value: 'locked' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('khóa tạm thời');
  });
});
```

---

### Task 15: Test — `Register.test.tsx`

**Files:**
- Create: `frontend/src/pages/auth/__tests__/Register.test.tsx`

- [ ] **Step 1: Write tests**

```tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Register from '../Register';
import { useAuthStore } from '../../../stores/authStore';

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>,
  );
}

describe('Register page', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, tenant: null, accessToken: null, refreshToken: null });
  });

  it('renders Vietnamese form labels', () => {
    renderRegister();
    expect(screen.getByText('Đăng ký shop mới')).toBeInTheDocument();
    expect(screen.getByText('Tên shop')).toBeInTheDocument();
  });

  it('submits and dispatches register, populating store', async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText('Tên shop'), { target: { value: 'Shop A' } });
    fireEvent.change(screen.getByLabelText('Tên chủ shop'), { target: { value: 'Chủ shop' } });
    fireEvent.change(screen.getByLabelText('Số điện thoại'), { target: { value: '0900000001' } });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), { target: { value: 'secret1' } });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));
    await waitFor(() => {
      expect(useAuthStore.getState().accessToken).toBe('access-1');
    });
  });

  it('rejects invalid phone format client-side', async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText('Tên shop'), { target: { value: 'Shop A' } });
    fireEvent.change(screen.getByLabelText('Tên chủ shop'), { target: { value: 'Chủ shop' } });
    fireEvent.change(screen.getByLabelText('Số điện thoại'), { target: { value: '123' } });
    fireEvent.change(screen.getByLabelText('Mật khẩu'), { target: { value: 'secret1' } });
    fireEvent.click(screen.getByRole('button', { name: /đăng ký/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('10 chữ số');
  });
});
```

---

### Task 16: Test — `StaffList.test.tsx`

**Files:**
- Create: `frontend/src/pages/staff/__tests__/StaffList.test.tsx`

- [ ] **Step 1: Write tests**

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__tests__/setup';
import StaffList from '../StaffList';

describe('StaffList page', () => {
  beforeEach(() => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders staff rows from API', async () => {
    render(
      <MemoryRouter>
        <StaffList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Nhân viên A')).toBeInTheDocument();
    expect(screen.getByText('CASHIER')).toBeInTheDocument();
  });

  it('triggers PATCH /staff/:id/deactivate when Khóa clicked', async () => {
    let called = false;
    server.use(
      http.patch('*/staff/:id/deactivate', ({ params }) => {
        called = true;
        return HttpResponse.json({
          id: Number(params.id),
          full_name: 'Nhân viên A',
          phone: '0900000002',
          email: null,
          role: 'CASHIER',
          is_active: false,
          last_login_at: null,
          created_at: '2026-05-22T00:00:00Z',
        });
      }),
    );

    render(
      <MemoryRouter>
        <StaffList />
      </MemoryRouter>,
    );
    const btn = await screen.findByRole('button', { name: 'Khóa' });
    fireEvent.click(btn);
    await waitFor(() => expect(called).toBe(true));
  });

  it('shows empty state when API returns no items', async () => {
    server.use(
      http.get('*/staff', () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, total_pages: 0 },
        }),
      ),
    );
    render(
      <MemoryRouter>
        <StaffList />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Chưa có nhân viên')).toBeInTheDocument();
  });
});
```

---

### Task 17: Run tsc + tests

- [ ] **Step 1: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0.

- [ ] **Step 2: Run all tests**

Run: `cd frontend && npm run test -- --run`
Expected: all suites pass; capture counts.

---

## Self-Review checklist

- [x] All routes in design covered (Login, Register, ChangePassword, StaffList in App.tsx).
- [x] All API functions in design implemented (auth.ts, staff.ts).
- [x] Store extensions match design (refreshToken, async login/register/doLogout).
- [x] Tests cover behaviors listed in design section 7.
- [x] No "TBD" or placeholder text.
- [x] Type names consistent across tasks (`LoginPendingSelection`, `StaffResponse`, `Pagination`).
