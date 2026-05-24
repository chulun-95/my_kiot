# Complete System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện toàn bộ hệ thống POS — fix backend compatibility, xây dựng frontend React từ đầu, và cấu hình deployment.

**Architecture:** Backend FastAPI đã hoàn chỉnh (6 module, 47 UC). Frontend React 18 + Vite + TypeScript + Tailwind + Zustand cần xây dựng mới hoàn toàn. Deployment trên 1 VPS với Nginx + Uvicorn.

**Tech Stack:** Python 3.11+ (FastAPI), React 18, Vite, TypeScript, Tailwind CSS v3, Zustand, Axios, React Router v6, Recharts (biểu đồ), React Hot Toast (notifications)

---

## Trạng thái hiện tại

| Module | Backend | Frontend | Tests |
|--------|---------|----------|-------|
| Auth & Tenant | ✅ Done | ❌ Missing | ✅ exists |
| Product & Categories | ✅ Done | ❌ Missing | ✅ exists |
| Customer & Supplier | ✅ Done | ❌ Missing | ✅ exists |
| Inventory & Goods Receipt | ✅ Done | ❌ Missing | ✅ exists |
| Sales / POS | ✅ Done | ❌ Missing | ✅ exists |
| Reports | ✅ Done | ❌ Missing | ✅ exists |

**Vấn đề cần fix ngay:**
1. `exceptions.py:19` dùng `dict[str, Any] | None` — Python 3.10+ syntax, lỗi trên Python 3.9
2. Frontend chưa tồn tại (không có `frontend/` directory)

---

## File Structure — Frontend

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api/
    │   ├── client.ts          # axios + auto-refresh interceptor
    │   ├── auth.ts            # auth API calls
    │   ├── products.ts        # product API calls
    │   ├── customers.ts
    │   ├── inventory.ts
    │   ├── sales.ts
    │   └── reports.ts
    ├── stores/
    │   └── authStore.ts       # Zustand: user, tenant, access_token
    ├── types/
    │   └── index.ts           # shared TypeScript interfaces
    ├── hooks/
    │   └── useDebounce.ts
    ├── components/
    │   ├── layout/
    │   │   ├── AppLayout.tsx  # Sidebar + Header + <Outlet>
    │   │   ├── Sidebar.tsx
    │   │   └── Header.tsx
    │   └── shared/
    │       ├── Pagination.tsx
    │       ├── ConfirmDialog.tsx
    │       ├── LoadingSpinner.tsx
    │       └── EmptyState.tsx
    └── pages/
        ├── auth/
        │   ├── LoginPage.tsx
        │   └── RegisterPage.tsx
        ├── dashboard/
        │   └── DashboardPage.tsx
        ├── products/
        │   ├── ProductListPage.tsx
        │   ├── ProductFormPage.tsx
        │   └── CategoryPage.tsx
        ├── customers/
        │   ├── CustomerListPage.tsx
        │   └── SupplierListPage.tsx
        ├── pos/
        │   ├── POSPage.tsx         # main POS screen
        │   └── InvoiceListPage.tsx
        ├── inventory/
        │   ├── GoodsReceiptListPage.tsx
        │   ├── GoodsReceiptFormPage.tsx
        │   ├── StockPage.tsx
        │   └── AdjustmentPage.tsx
        └── reports/
            ├── RevenuePage.tsx
            ├── TopProductsPage.tsx
            └── ProfitPage.tsx
```

---

## Phase 1 — Backend Stabilization

### Task 1: Fix Python 3.9 Compatibility

**Files:**
- Modify: `backend/exceptions.py`
- Modify: `backend/modules/*/service.py`, `backend/modules/*/schemas.py` (scan for `X | None` syntax)

- [ ] **Step 1: Fix `exceptions.py` — union type syntax**

Replace `dict[str, Any] | None` with `Optional[dict[str, Any]]`:

```python
# backend/exceptions.py
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Request
...

class AppError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[dict] = None,
    ):
```

- [ ] **Step 2: Scan and fix all other union type syntax in backend**

```bash
grep -rn " | None" backend/ --include="*.py" | grep -v "# noqa"
```

For each hit like `str | None`, replace with `Optional[str]` and add `from typing import Optional` if not present.

- [ ] **Step 3: Verify tests can at least import**

```bash
cd /Users/vuongnv/Documents/my_kiot
python3 -c "from backend.main import app; print('OK')"
```

Expected: `OK` (no ImportError)

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all tests pass or at most known failures

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "fix: Python 3.9 compatibility — replace X|None with Optional[X]"
```

---

## Phase 2 — Frontend Foundation

### Task 2: Vite + React Project Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Init Vite project**

```bash
cd /Users/vuongnv/Documents/my_kiot
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install axios zustand react-router-dom@6 react-hot-toast recharts
npm install -D tailwindcss@3 postcss autoprefixer @types/node
npx tailwindcss init -p
```

- [ ] **Step 2: Configure Tailwind** — edit `frontend/tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

Add to `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 3: Configure Vite proxy** — edit `frontend/vite.config.ts`

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true }
    }
  }
})
```

- [ ] **Step 4: Create TypeScript types** — create `frontend/src/types/index.ts`

```ts
export interface Tenant {
  id: number
  name: string
  slug: string
}

export interface User {
  id: number
  full_name: string
  phone: string | null
  email: string | null
  role: 'OWNER' | 'CASHIER'
}

export interface Pagination {
  page: number
  limit: number
  total: number
  total_pages: number
}

export interface Product {
  id: number
  sku: string
  barcode: string | null
  name: string
  unit: string
  cost_price: number | null
  sale_price: number
  min_stock: number
  image_url: string | null
  status: 'ACTIVE' | 'INACTIVE' | 'DRAFT'
  allow_negative: boolean
  category_id: number | null
  category_name: string | null
  units: ProductUnit[]
}

export interface ProductUnit {
  id: number
  unit_name: string
  conversion_rate: number
  sale_price: number | null
  barcode: string | null
}

export interface Category {
  id: number
  name: string
  depth: number
  sort_order: number
  children: Category[]
}

export interface Customer {
  id: number
  name: string
  phone: string | null
  email: string | null
  address: string | null
  total_spent: number
  total_orders: number
}

export interface Supplier {
  id: number
  name: string
  phone: string | null
  email: string | null
  address: string | null
}

export interface InvoiceItem {
  product_id: number
  product_name: string
  product_sku: string
  unit: string | null
  quantity: number
  unit_price: number
  cost_price: number
  discount_amount: number
  line_total: number
  unit_id: number | null
  conversion_rate: number | null
}

export interface Invoice {
  id: number
  code: string
  customer_id: number | null
  cashier_id: number
  subtotal: number
  discount_amount: number
  total: number
  paid_amount: number
  change_amount: number
  status: 'DRAFT' | 'COMPLETED' | 'CANCELLED'
  note: string | null
  completed_at: string | null
  items: InvoiceItem[]
  payments: Payment[]
}

export interface Payment {
  id: number
  method: string
  amount: number
  note: string | null
}

export interface GoodsReceipt {
  id: number
  code: string
  supplier_id: number | null
  total: number
  paid_amount: number
  status: 'DRAFT' | 'COMPLETED' | 'CANCELLED'
  note: string | null
  completed_at: string | null
  items: GoodsReceiptItem[]
}

export interface GoodsReceiptItem {
  id: number
  product_id: number
  quantity: number
  cost_price: number
  line_total: number
  unit_id: number | null
  unit_name: string | null
  conversion_rate: number | null
}

export interface InventoryRow {
  product_id: number
  product_sku: string
  product_name: string
  unit: string
  quantity: number
  min_stock: number
  cost_price: number
  sale_price: number
}
```

- [ ] **Step 5: Verify project runs**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — expect Vite default page.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: init React frontend with Vite + Tailwind + Zustand"
```

---

### Task 3: Auth Store + API Client

**Files:**
- Create: `frontend/src/stores/authStore.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`

- [ ] **Step 1: Create Zustand auth store** — `frontend/src/stores/authStore.ts`

```ts
import { create } from 'zustand'
import type { User, Tenant } from '../types'

interface AuthState {
  user: User | null
  tenant: Tenant | null
  accessToken: string | null
  setAuth: (user: User, tenant: Tenant, token: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tenant: null,
  accessToken: null,
  setAuth: (user, tenant, accessToken) => set({ user, tenant, accessToken }),
  clearAuth: () => set({ user: null, tenant: null, accessToken: null }),
}))
```

- [ ] **Step 2: Create axios client with interceptor** — `frontend/src/api/client.ts`

```ts
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const client = axios.create({ baseURL: '/api/v1' })

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const rt = localStorage.getItem('refresh_token')
        if (!rt) throw new Error('no refresh token')
        const res = await axios.post('/api/v1/auth/refresh', { refresh_token: rt })
        const newToken = res.data.access_token
        useAuthStore.getState().setAuth(
          useAuthStore.getState().user!,
          useAuthStore.getState().tenant!,
          newToken,
        )
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      } catch {
        useAuthStore.getState().clearAuth()
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default client
```

- [ ] **Step 3: Create auth API** — `frontend/src/api/auth.ts`

```ts
import client from './client'
import axios from 'axios'

export async function login(phone: string, password: string) {
  const res = await axios.post('/api/v1/auth/login', { phone, password })
  return res.data
}

export async function register(data: {
  shop_name: string
  owner_name: string
  phone: string
  password: string
}) {
  const res = await axios.post('/api/v1/auth/register', data)
  return res.data
}

export async function logout(refreshToken: string) {
  await client.post('/auth/logout', { refresh_token: refreshToken })
}

export async function getMe() {
  const res = await client.get('/auth/me')
  return res.data
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores frontend/src/api/client.ts frontend/src/api/auth.ts
git commit -m "feat: auth store + axios client with token refresh interceptor"
```

---

### Task 4: App Router + Layout

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/layout/AppLayout.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/Header.tsx`

- [ ] **Step 1: Setup main.tsx**

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster position="top-right" />
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 2: Setup App.tsx with routes**

```tsx
// frontend/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import ProductListPage from './pages/products/ProductListPage'
import CategoryPage from './pages/products/CategoryPage'
import CustomerListPage from './pages/customers/CustomerListPage'
import SupplierListPage from './pages/customers/SupplierListPage'
import POSPage from './pages/pos/POSPage'
import InvoiceListPage from './pages/pos/InvoiceListPage'
import GoodsReceiptListPage from './pages/inventory/GoodsReceiptListPage'
import StockPage from './pages/inventory/StockPage'
import RevenuePage from './pages/reports/RevenuePage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<RequireAuth><AppLayout /></RequireAuth>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="products" element={<ProductListPage />} />
        <Route path="categories" element={<CategoryPage />} />
        <Route path="customers" element={<CustomerListPage />} />
        <Route path="suppliers" element={<SupplierListPage />} />
        <Route path="pos" element={<POSPage />} />
        <Route path="invoices" element={<InvoiceListPage />} />
        <Route path="goods-receipts" element={<GoodsReceiptListPage />} />
        <Route path="stock" element={<StockPage />} />
        <Route path="reports/revenue" element={<RevenuePage />} />
      </Route>
    </Routes>
  )
}
```

- [ ] **Step 3: Create Sidebar** — `frontend/src/components/layout/Sidebar.tsx`

```tsx
import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

const nav = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/pos', label: 'Bán hàng' },
  { to: '/invoices', label: 'Hóa đơn' },
  { to: '/products', label: 'Sản phẩm' },
  { to: '/categories', label: 'Nhóm hàng' },
  { to: '/customers', label: 'Khách hàng' },
  { to: '/suppliers', label: 'Nhà cung cấp' },
  { to: '/goods-receipts', label: 'Nhập hàng' },
  { to: '/stock', label: 'Tồn kho' },
  { to: '/reports/revenue', label: 'Báo cáo' },
]

export default function Sidebar() {
  const tenant = useAuthStore((s) => s.tenant)
  return (
    <aside className="w-56 bg-gray-900 text-gray-100 flex flex-col min-h-screen">
      <div className="p-4 font-bold text-lg border-b border-gray-700 truncate">
        {tenant?.name ?? 'POS'}
      </div>
      <nav className="flex-1 p-2">
        {nav.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `block px-3 py-2 rounded text-sm mb-1 ${isActive ? 'bg-blue-600' : 'hover:bg-gray-700'}`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
```

- [ ] **Step 4: Create Header** — `frontend/src/components/layout/Header.tsx`

```tsx
import { useAuthStore } from '../../stores/authStore'
import { logout } from '../../api/auth'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

export default function Header() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    const rt = localStorage.getItem('refresh_token') ?? ''
    try { await logout(rt) } catch {}
    localStorage.removeItem('refresh_token')
    clearAuth()
    navigate('/login')
    toast.success('Đã đăng xuất')
  }

  return (
    <header className="h-12 bg-white border-b flex items-center justify-end px-4 gap-4">
      <span className="text-sm text-gray-600">{user?.full_name} ({user?.role})</span>
      <button onClick={handleLogout} className="text-sm text-red-500 hover:underline">
        Đăng xuất
      </button>
    </header>
  )
}
```

- [ ] **Step 5: Create AppLayout** — `frontend/src/components/layout/AppLayout.tsx`

```tsx
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Create placeholder pages** for every route in App.tsx so the app builds.

For each missing page, create a minimal file:
```tsx
// e.g. frontend/src/pages/dashboard/DashboardPage.tsx
export default function DashboardPage() {
  return <div className="text-xl font-semibold">Dashboard</div>
}
```

Repeat for: `ProductListPage`, `CategoryPage`, `CustomerListPage`, `SupplierListPage`, `POSPage`, `InvoiceListPage`, `GoodsReceiptListPage`, `StockPage`, `RevenuePage`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: app routing + sidebar + header layout"
```

---

## Phase 3 — Auth Pages

### Task 5: Login & Register Pages

**Files:**
- Create: `frontend/src/pages/auth/LoginPage.tsx`
- Create: `frontend/src/pages/auth/RegisterPage.tsx`

- [ ] **Step 1: LoginPage**

```tsx
// frontend/src/pages/auth/LoginPage.tsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../../api/auth'
import { useAuthStore } from '../../stores/authStore'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await login(phone, password)
      if (data.requires_tenant_selection) {
        toast.error('Nhiều shop: chưa hỗ trợ chọn shop, liên hệ admin.')
        return
      }
      localStorage.setItem('refresh_token', data.refresh_token)
      setAuth(data.user, data.tenant, data.access_token)
      navigate('/dashboard')
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message ?? 'Đăng nhập thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white rounded-xl shadow p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">Đăng nhập</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Số điện thoại</label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="0901234567"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Mật khẩu</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>
        <p className="mt-4 text-sm text-center text-gray-500">
          Chưa có tài khoản? <Link to="/register" className="text-blue-600 hover:underline">Đăng ký</Link>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: RegisterPage**

```tsx
// frontend/src/pages/auth/RegisterPage.tsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../../api/auth'
import { useAuthStore } from '../../stores/authStore'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const [form, setForm] = useState({ shop_name: '', owner_name: '', phone: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await register(form)
      localStorage.setItem('refresh_token', data.refresh_token)
      setAuth(data.user, data.tenant, data.access_token)
      navigate('/dashboard')
      toast.success('Đăng ký thành công!')
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message ?? 'Đăng ký thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white rounded-xl shadow p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">Đăng ký shop</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: 'shop_name', label: 'Tên shop', type: 'text', placeholder: 'Tạp hóa Minh Anh' },
            { key: 'owner_name', label: 'Tên chủ shop', type: 'text', placeholder: 'Nguyễn Minh Anh' },
            { key: 'phone', label: 'Số điện thoại', type: 'tel', placeholder: '0901234567' },
            { key: 'password', label: 'Mật khẩu', type: 'password', placeholder: 'Tối thiểu 6 ký tự' },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key}>
              <label className="block text-sm font-medium mb-1">{label}</label>
              <input
                type={type}
                value={form[key as keyof typeof form]}
                onChange={set(key)}
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={placeholder}
                required
              />
            </div>
          ))}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Đang tạo...' : 'Đăng ký'}
          </button>
        </form>
        <p className="mt-4 text-sm text-center text-gray-500">
          Đã có tài khoản? <Link to="/login" className="text-blue-600 hover:underline">Đăng nhập</Link>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Test login flow manually**

```bash
# Start backend: cd /Users/vuongnv/Documents/my_kiot && uvicorn backend.main:app --reload
# Start frontend: cd frontend && npm run dev
```

Open http://localhost:5173/register → fill form → submit → should redirect to /dashboard.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/auth/
git commit -m "feat: login + register pages"
```

---

## Phase 4 — Dashboard

### Task 6: Dashboard Page

**Files:**
- Create: `frontend/src/api/reports.ts`
- Modify: `frontend/src/pages/dashboard/DashboardPage.tsx`

- [ ] **Step 1: Create reports API** — `frontend/src/api/reports.ts`

```ts
import client from './client'

export async function getDashboard() {
  const res = await client.get('/reports/dashboard')
  return res.data
}

export async function getRevenue(params: { from: string; to: string; group_by?: string }) {
  const res = await client.get('/reports/revenue', { params })
  return res.data
}

export async function getTopProducts(params: { from: string; to: string; limit?: number }) {
  const res = await client.get('/reports/top-products', { params })
  return res.data
}

export async function getProfit(params: { from: string; to: string }) {
  const res = await client.get('/reports/profit', { params })
  return res.data
}
```

- [ ] **Step 2: DashboardPage** — `frontend/src/pages/dashboard/DashboardPage.tsx`

```tsx
import { useEffect, useState } from 'react'
import { getDashboard } from '../../api/reports'
import toast from 'react-hot-toast'

interface DashboardData {
  today_revenue: number
  today_invoices: number
  today_profit: number
  today_customers: number
  pending_drafts: number
  low_stock_count: number
  inventory_value: number
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

function fmt(n: number) {
  return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + ' ₫'
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => toast.error('Không tải được dashboard'))
  }, [])

  if (!data) return <div className="text-gray-400">Đang tải...</div>

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">Dashboard hôm nay</h1>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Doanh thu" value={fmt(data.today_revenue)} />
        <StatCard label="Lợi nhuận" value={fmt(data.today_profit)} />
        <StatCard label="Hóa đơn" value={String(data.today_invoices)} />
        <StatCard label="Khách hàng" value={String(data.today_customers)} />
        <StatCard label="Hóa đơn treo" value={String(data.pending_drafts)} />
        <StatCard label="Hàng sắp hết" value={String(data.low_stock_count)} sub="Cần nhập thêm" />
        <StatCard label="Giá trị tồn kho" value={fmt(data.inventory_value)} />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/dashboard/ frontend/src/api/reports.ts
git commit -m "feat: dashboard page with stats"
```

---

## Phase 5 — Product Management

### Task 7: Product API + List Page

**Files:**
- Create: `frontend/src/api/products.ts`
- Modify: `frontend/src/pages/products/ProductListPage.tsx`

- [ ] **Step 1: Product API** — `frontend/src/api/products.ts`

```ts
import client from './client'

export async function getProducts(params?: {
  page?: number; limit?: number; search?: string; category_id?: number; status?: string
}) {
  const res = await client.get('/products', { params })
  return res.data
}

export async function getProduct(id: number) {
  const res = await client.get(`/products/${id}`)
  return res.data
}

export async function createProduct(data: object) {
  const res = await client.post('/products', data)
  return res.data
}

export async function updateProduct(id: number, data: object) {
  const res = await client.put(`/products/${id}`, data)
  return res.data
}

export async function deleteProduct(id: number) {
  await client.delete(`/products/${id}`)
}

export async function searchProducts(q: string, limit = 20) {
  const res = await client.get('/products/search', { params: { q, limit } })
  return res.data
}

export async function getProductByBarcode(code: string) {
  const res = await client.get(`/products/barcode/${code}`)
  return res.data
}

export async function getCategories() {
  const res = await client.get('/categories')
  return res.data
}

export async function createCategory(data: object) {
  const res = await client.post('/categories', data)
  return res.data
}

export async function updateCategory(id: number, data: object) {
  const res = await client.put(`/categories/${id}`, data)
  return res.data
}

export async function deleteCategory(id: number) {
  await client.delete(`/categories/${id}`)
}
```

- [ ] **Step 2: ProductListPage** — `frontend/src/pages/products/ProductListPage.tsx`

```tsx
import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getProducts, deleteProduct } from '../../api/products'
import type { Product, Pagination as PaginationType } from '../../types'
import toast from 'react-hot-toast'

function fmt(n: number) {
  return new Intl.NumberFormat('vi-VN').format(n)
}

export default function ProductListPage() {
  const [items, setItems] = useState<Product[]>([])
  const [pagination, setPagination] = useState<PaginationType | null>(null)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getProducts({ page, limit: 20, search: search || undefined })
      setItems(data.items)
      setPagination(data.pagination)
    } catch {
      toast.error('Không tải được danh sách sản phẩm')
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Ngừng bán "${name}"?`)) return
    try {
      await deleteProduct(id)
      toast.success('Đã ngừng bán')
      load()
    } catch {
      toast.error('Lỗi khi xóa sản phẩm')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Sản phẩm</h1>
        <Link to="/products/new" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          + Thêm SP
        </Link>
      </div>

      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          placeholder="Tìm tên, SKU, barcode..."
          className="border rounded px-3 py-2 w-72 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {loading ? (
        <div className="text-gray-400">Đang tải...</div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3">SKU</th>
                <th className="text-left px-4 py-3">Tên sản phẩm</th>
                <th className="text-left px-4 py-3">ĐVT</th>
                <th className="text-right px-4 py-3">Giá bán</th>
                <th className="text-center px-4 py-3">Trạng thái</th>
                <th className="text-center px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map(p => (
                <tr key={p.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{p.sku}</td>
                  <td className="px-4 py-2">
                    <div className="font-medium">{p.name}</div>
                    {p.barcode && <div className="text-xs text-gray-400">{p.barcode}</div>}
                  </td>
                  <td className="px-4 py-2">{p.unit}</td>
                  <td className="px-4 py-2 text-right">{fmt(p.sale_price)}</td>
                  <td className="px-4 py-2 text-center">
                    <span className={`text-xs px-2 py-1 rounded-full ${p.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">
                    <Link to={`/products/${p.id}/edit`} className="text-blue-500 hover:underline mr-3">Sửa</Link>
                    <button onClick={() => handleDelete(p.id, p.name)} className="text-red-400 hover:underline">Xóa</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {pagination && (
            <div className="px-4 py-3 flex items-center justify-between text-sm text-gray-500">
              <span>Tổng: {pagination.total} sản phẩm</span>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border rounded disabled:opacity-40">Trước</button>
                <span className="px-3 py-1">{page}/{pagination.total_pages}</span>
                <button disabled={page >= pagination.total_pages} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border rounded disabled:opacity-40">Sau</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Add route for product form** — add to App.tsx

```tsx
import ProductFormPage from './pages/products/ProductFormPage'
// ... inside routes:
<Route path="products/new" element={<ProductFormPage />} />
<Route path="products/:id/edit" element={<ProductFormPage />} />
```

- [ ] **Step 4: ProductFormPage** — `frontend/src/pages/products/ProductFormPage.tsx`

```tsx
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getProduct, createProduct, updateProduct } from '../../api/products'
import toast from 'react-hot-toast'

const UNITS = ['cái', 'gói', 'chai', 'lon', 'kg', 'lạng', 'lít', 'thùng', 'lốc', 'hộp', 'túi', 'bịch', 'cuộn']

export default function ProductFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    name: '', sku: '', barcode: '', unit: 'cái',
    cost_price: 0, sale_price: 0, min_stock: 0,
    description: '', status: 'ACTIVE', allow_negative: false,
  })

  useEffect(() => {
    if (!id) return
    getProduct(Number(id)).then(p => {
      setForm({
        name: p.name, sku: p.sku, barcode: p.barcode ?? '',
        unit: p.unit, cost_price: p.cost_price ?? 0,
        sale_price: p.sale_price, min_stock: p.min_stock,
        description: p.description ?? '', status: p.status,
        allow_negative: p.allow_negative,
      })
    })
  }, [id])

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const v = e.target.type === 'checkbox' ? (e.target as HTMLInputElement).checked : e.target.value
    setForm(f => ({ ...f, [k]: v }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    const body = {
      ...form,
      cost_price: Number(form.cost_price),
      sale_price: Number(form.sale_price),
      min_stock: Number(form.min_stock),
      barcode: form.barcode || null,
    }
    try {
      if (isEdit) {
        await updateProduct(Number(id), body)
        toast.success('Đã cập nhật sản phẩm')
      } else {
        await createProduct(body)
        toast.success('Đã tạo sản phẩm')
      }
      navigate('/products')
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message ?? 'Có lỗi xảy ra')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-bold mb-6">{isEdit ? 'Sửa sản phẩm' : 'Thêm sản phẩm'}</h1>
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Tên sản phẩm *</label>
            <input value={form.name} onChange={set('name')} required className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">SKU</label>
            <input value={form.sku} onChange={set('sku')} placeholder="Tự sinh nếu để trống" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Barcode</label>
            <input value={form.barcode} onChange={set('barcode')} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Đơn vị</label>
            <select value={form.unit} onChange={set('unit')} className="w-full border rounded px-3 py-2">
              {UNITS.map(u => <option key={u}>{u}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Giá vốn</label>
            <input type="number" min={0} value={form.cost_price} onChange={set('cost_price')} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Giá bán *</label>
            <input type="number" min={0} value={form.sale_price} onChange={set('sale_price')} required className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tồn kho tối thiểu</label>
            <input type="number" min={0} value={form.min_stock} onChange={set('min_stock')} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Trạng thái</label>
            <select value={form.status} onChange={set('status')} className="w-full border rounded px-3 py-2">
              <option value="ACTIVE">Đang bán</option>
              <option value="INACTIVE">Ngừng bán</option>
            </select>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id="allow_neg" checked={form.allow_negative} onChange={set('allow_negative')} />
          <label htmlFor="allow_neg" className="text-sm">Cho phép tồn kho âm</label>
        </div>
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
            {loading ? 'Đang lưu...' : 'Lưu'}
          </button>
          <button type="button" onClick={() => navigate('/products')} className="border px-6 py-2 rounded hover:bg-gray-50">
            Hủy
          </button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/products/ frontend/src/api/products.ts
git commit -m "feat: product list + create/edit form"
```

---

## Phase 6 — POS Screen (most complex)

### Task 8: POS Screen

**Files:**
- Create: `frontend/src/pages/pos/POSPage.tsx`

The POS screen has two panels: left = product search + cart, right = payment.

- [ ] **Step 1: POSPage — full implementation**

```tsx
// frontend/src/pages/pos/POSPage.tsx
import { useState, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'
import { searchProducts, getProductByBarcode } from '../../api/products'
import client from '../../api/client'
import type { Product, ProductUnit } from '../../types'

interface CartItem {
  product_id: number
  product_name: string
  unit: string
  quantity: number
  unit_price: number
  discount_amount: number
  unit_id: number | null
  conversion_rate: number | null
}

function fmt(n: number) {
  return new Intl.NumberFormat('vi-VN').format(Math.round(n))
}

export default function POSPage() {
  const [cart, setCart] = useState<CartItem[]>([])
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState<Product[]>([])
  const [showSearch, setShowSearch] = useState(false)
  const [discount, setDiscount] = useState(0)
  const [paying, setPaying] = useState(false)
  const [cashAmount, setCashAmount] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)

  const subtotal = cart.reduce((s, i) => s + i.unit_price * i.quantity - i.discount_amount, 0)
  const total = Math.max(0, subtotal - discount)
  const cashNum = Number(cashAmount) || 0
  const change = Math.max(0, cashNum - total)

  const addToCart = useCallback((product: Product, unit?: ProductUnit) => {
    const pid = product.id
    const uid = unit?.id ?? null
    const price = unit?.sale_price ?? (unit ? product.sale_price * unit.conversion_rate : product.sale_price)
    const unitName = unit?.unit_name ?? product.unit
    const convRate = unit?.conversion_rate ?? null

    setCart(prev => {
      const idx = prev.findIndex(i => i.product_id === pid && i.unit_id === uid)
      if (idx >= 0) {
        const next = [...prev]
        next[idx] = { ...next[idx], quantity: next[idx].quantity + 1 }
        return next
      }
      return [...prev, {
        product_id: pid,
        product_name: product.name,
        unit: unitName,
        quantity: 1,
        unit_price: price,
        discount_amount: 0,
        unit_id: uid,
        conversion_rate: convRate,
      }]
    })
    setShowSearch(false)
    setSearchQ('')
    setSearchResults([])
    searchRef.current?.focus()
  }, [])

  const handleSearch = async (q: string) => {
    setSearchQ(q)
    if (!q.trim()) { setShowSearch(false); return }
    // Try barcode first
    if (/^\d{8,14}$/.test(q.trim())) {
      try {
        const p = await getProductByBarcode(q.trim())
        addToCart(p, p.matched_unit)
        return
      } catch {}
    }
    const data = await searchProducts(q, 10)
    setSearchResults(data.items)
    setShowSearch(true)
  }

  const updateQty = (idx: number, qty: number) => {
    if (qty <= 0) {
      setCart(prev => prev.filter((_, i) => i !== idx))
    } else {
      setCart(prev => prev.map((item, i) => i === idx ? { ...item, quantity: qty } : item))
    }
  }

  const updatePrice = (idx: number, price: number) => {
    setCart(prev => prev.map((item, i) => i === idx ? { ...item, unit_price: price } : item))
  }

  const handleComplete = async () => {
    if (!cart.length) { toast.error('Giỏ hàng trống'); return }
    if (cashNum < total) { toast.error('Tiền nhận chưa đủ'); return }
    try {
      // Create invoice
      const inv = await client.post('/invoices', {
        items: cart.map(i => ({
          product_id: i.product_id,
          quantity: i.quantity,
          unit_price: i.unit_price,
          discount_amount: i.discount_amount,
          unit_id: i.unit_id,
        })),
        discount_amount: discount,
      })
      // Complete invoice
      await client.post(`/invoices/${inv.data.id}/complete`, {
        payments: [{ method: 'CASH', amount: cashNum }],
        allow_debt: false,
      })
      toast.success(`Hoàn tất! Tiền thối: ${fmt(change)} ₫`)
      setCart([])
      setDiscount(0)
      setCashAmount('')
      setPaying(false)
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message ?? 'Lỗi thanh toán')
    }
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-4">
      {/* LEFT — search + cart */}
      <div className="flex-1 flex flex-col bg-white rounded-xl shadow overflow-hidden">
        {/* Search bar */}
        <div className="relative p-3 border-b">
          <input
            ref={searchRef}
            value={searchQ}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Quét barcode hoặc tìm tên SP..."
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          {showSearch && searchResults.length > 0 && (
            <div className="absolute left-3 right-3 top-full mt-1 bg-white border rounded shadow-lg z-10 max-h-64 overflow-y-auto">
              {searchResults.map(p => (
                <button
                  key={p.id}
                  onClick={() => addToCart(p)}
                  className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b last:border-0"
                >
                  <div className="font-medium text-sm">{p.name}</div>
                  <div className="text-xs text-gray-400">{p.sku} — {fmt(p.sale_price)} ₫/{p.unit}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Cart items */}
        <div className="flex-1 overflow-y-auto">
          {cart.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-300 text-sm">
              Giỏ hàng trống
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left px-3 py-2">Sản phẩm</th>
                  <th className="text-center px-3 py-2 w-24">Số lượng</th>
                  <th className="text-right px-3 py-2 w-28">Đơn giá</th>
                  <th className="text-right px-3 py-2 w-28">Thành tiền</th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody>
                {cart.map((item, idx) => (
                  <tr key={idx} className="border-b">
                    <td className="px-3 py-2">
                      {item.product_name}
                      <span className="text-xs text-gray-400 ml-1">/{item.unit}</span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-center gap-1">
                        <button onClick={() => updateQty(idx, item.quantity - 1)} className="w-6 h-6 border rounded text-center hover:bg-gray-100">-</button>
                        <input
                          type="number" min={0} step={0.001}
                          value={item.quantity}
                          onChange={e => updateQty(idx, Number(e.target.value))}
                          className="w-16 border rounded text-center px-1 py-0.5"
                        />
                        <button onClick={() => updateQty(idx, item.quantity + 1)} className="w-6 h-6 border rounded text-center hover:bg-gray-100">+</button>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number" min={0}
                        value={item.unit_price}
                        onChange={e => updatePrice(idx, Number(e.target.value))}
                        className="w-full border rounded px-2 py-0.5 text-right"
                      />
                    </td>
                    <td className="px-3 py-2 text-right font-medium">
                      {fmt(item.unit_price * item.quantity - item.discount_amount)}
                    </td>
                    <td className="px-1 py-2">
                      <button onClick={() => setCart(c => c.filter((_, i) => i !== idx))} className="text-red-400 hover:text-red-600 text-xs">✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer totals */}
        <div className="border-t p-3 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Tạm tính</span>
            <span>{fmt(subtotal)} ₫</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-500">Giảm giá HĐ</span>
            <input
              type="number" min={0} value={discount}
              onChange={e => setDiscount(Number(e.target.value))}
              className="w-32 border rounded px-2 py-0.5 text-right"
            />
          </div>
          <div className="flex justify-between font-bold text-base">
            <span>Tổng cộng</span>
            <span className="text-blue-600">{fmt(total)} ₫</span>
          </div>
        </div>
      </div>

      {/* RIGHT — payment */}
      <div className="w-72 bg-white rounded-xl shadow p-4 flex flex-col gap-4">
        <h2 className="font-bold text-lg">Thanh toán</h2>

        <div>
          <label className="block text-sm text-gray-500 mb-1">Khách đưa</label>
          <input
            type="number" min={0}
            value={cashAmount}
            onChange={e => setCashAmount(e.target.value)}
            placeholder="0"
            className="w-full border rounded px-3 py-2 text-xl font-bold text-right focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Quick amounts */}
        <div className="grid grid-cols-3 gap-2">
          {[50000, 100000, 200000, 500000, 1000000].map(n => (
            <button
              key={n}
              onClick={() => setCashAmount(String(Math.ceil(total / n) * n))}
              className="border rounded py-1 text-xs hover:bg-blue-50"
            >
              {fmt(Math.ceil(total / n) * n)}
            </button>
          ))}
          <button
            onClick={() => setCashAmount(String(total))}
            className="border rounded py-1 text-xs bg-blue-50 font-medium"
          >
            Đúng tiền
          </button>
        </div>

        <div className="bg-gray-50 rounded p-3 space-y-1 text-sm">
          <div className="flex justify-between">
            <span>Cần thanh toán</span>
            <span className="font-bold">{fmt(total)} ₫</span>
          </div>
          <div className="flex justify-between text-green-600">
            <span>Tiền thối</span>
            <span className="font-bold">{fmt(change)} ₫</span>
          </div>
        </div>

        <button
          onClick={handleComplete}
          disabled={!cart.length || cashNum < total}
          className="mt-auto w-full bg-green-600 text-white py-3 rounded-xl font-bold text-lg hover:bg-green-700 disabled:opacity-40"
        >
          Thanh toán (F9)
        </button>

        <button
          onClick={() => { setCart([]); setDiscount(0); setCashAmount('') }}
          className="w-full border text-red-500 py-2 rounded hover:bg-red-50 text-sm"
        >
          Hủy giỏ hàng
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: InvoiceListPage** — `frontend/src/pages/pos/InvoiceListPage.tsx`

```tsx
import { useEffect, useState, useCallback } from 'react'
import client from '../../api/client'
import type { Invoice, Pagination as PaginationType } from '../../types'
import toast from 'react-hot-toast'

function fmt(n: number) { return new Intl.NumberFormat('vi-VN').format(Math.round(n)) }

export default function InvoiceListPage() {
  const [items, setItems] = useState<Invoice[]>([])
  const [pagination, setPagination] = useState<PaginationType | null>(null)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')

  const load = useCallback(async () => {
    try {
      const params: any = { page, limit: 20 }
      if (status) params.status = status
      const res = await client.get('/invoices', { params })
      setItems(res.data.items)
      setPagination(res.data.pagination)
    } catch { toast.error('Lỗi tải hóa đơn') }
  }, [page, status])

  useEffect(() => { load() }, [load])

  const handleCancel = async (id: number) => {
    const reason = prompt('Lý do hủy:')
    if (reason === null) return
    try {
      await client.post(`/invoices/${id}/cancel`, { reason })
      toast.success('Đã hủy hóa đơn')
      load()
    } catch (err: any) { toast.error(err?.response?.data?.error?.message ?? 'Lỗi hủy') }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Lịch sử hóa đơn</h1>
      <div className="mb-4 flex gap-2">
        {['', 'DRAFT', 'COMPLETED', 'CANCELLED'].map(s => (
          <button key={s} onClick={() => { setStatus(s); setPage(1) }}
            className={`px-3 py-1 rounded border text-sm ${status === s ? 'bg-blue-600 text-white' : 'hover:bg-gray-50'}`}>
            {s || 'Tất cả'}
          </button>
        ))}
      </div>
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3">Mã HĐ</th>
              <th className="text-right px-4 py-3">Tổng tiền</th>
              <th className="text-center px-4 py-3">Trạng thái</th>
              <th className="text-left px-4 py-3">Thời gian</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {items.map(inv => (
              <tr key={inv.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{inv.code}</td>
                <td className="px-4 py-2 text-right">{fmt(inv.total)} ₫</td>
                <td className="px-4 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    inv.status === 'COMPLETED' ? 'bg-green-100 text-green-700'
                    : inv.status === 'CANCELLED' ? 'bg-red-100 text-red-600'
                    : 'bg-yellow-100 text-yellow-700'
                  }`}>{inv.status}</span>
                </td>
                <td className="px-4 py-2 text-xs text-gray-400">
                  {new Date(inv.completed_at ?? '').toLocaleString('vi-VN')}
                </td>
                <td className="px-4 py-2">
                  {inv.status === 'COMPLETED' && (
                    <button onClick={() => handleCancel(inv.id)} className="text-red-400 text-xs hover:underline">Hủy</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {pagination && (
          <div className="px-4 py-3 flex justify-between text-sm text-gray-500">
            <span>Tổng: {pagination.total}</span>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border rounded disabled:opacity-40">Trước</button>
              <span>{page}/{pagination.total_pages}</span>
              <button disabled={page >= pagination.total_pages} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border rounded disabled:opacity-40">Sau</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/pos/
git commit -m "feat: POS screen + invoice list"
```

---

## Phase 7 — Customer & Supplier Pages

### Task 9: Customer + Supplier Management

**Files:**
- Create: `frontend/src/api/customers.ts`
- Create: `frontend/src/pages/customers/CustomerListPage.tsx`
- Create: `frontend/src/pages/customers/SupplierListPage.tsx`

- [ ] **Step 1: Customers API** — `frontend/src/api/customers.ts`

```ts
import client from './client'

export async function getCustomers(params?: { page?: number; search?: string }) {
  const res = await client.get('/customers', { params })
  return res.data
}

export async function createCustomer(data: object) {
  const res = await client.post('/customers', data)
  return res.data
}

export async function updateCustomer(id: number, data: object) {
  const res = await client.put(`/customers/${id}`, data)
  return res.data
}

export async function getSuppliers(params?: { page?: number; search?: string }) {
  const res = await client.get('/suppliers', { params })
  return res.data
}

export async function createSupplier(data: object) {
  const res = await client.post('/suppliers', data)
  return res.data
}

export async function updateSupplier(id: number, data: object) {
  const res = await client.put(`/suppliers/${id}`, data)
  return res.data
}
```

- [ ] **Step 2: CustomerListPage** — `frontend/src/pages/customers/CustomerListPage.tsx`

```tsx
import { useEffect, useState, useCallback } from 'react'
import { getCustomers, createCustomer } from '../../api/customers'
import type { Customer } from '../../types'
import toast from 'react-hot-toast'

function fmt(n: number) { return new Intl.NumberFormat('vi-VN').format(Math.round(n)) }

export default function CustomerListPage() {
  const [items, setItems] = useState<Customer[]>([])
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', phone: '', email: '', address: '' })

  const load = useCallback(async () => {
    try {
      const d = await getCustomers({ page: 1, search: search || undefined })
      setItems(d.items)
    } catch { toast.error('Lỗi tải danh sách') }
  }, [search])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createCustomer(form)
      toast.success('Đã thêm khách hàng')
      setShowForm(false)
      setForm({ name: '', phone: '', email: '', address: '' })
      load()
    } catch (err: any) { toast.error(err?.response?.data?.error?.message ?? 'Lỗi') }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Khách hàng</h1>
        <button onClick={() => setShowForm(true)} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          + Thêm KH
        </button>
      </div>
      <input value={search} onChange={e => setSearch(e.target.value)}
        placeholder="Tìm tên, SĐT..." className="border rounded px-3 py-2 w-64 mb-4" />

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <form onSubmit={handleCreate} className="bg-white rounded-xl shadow p-6 w-96 space-y-3">
            <h2 className="font-bold text-lg">Thêm khách hàng</h2>
            {[
              { k: 'name', label: 'Tên *', type: 'text', required: true },
              { k: 'phone', label: 'SĐT', type: 'tel', required: false },
              { k: 'email', label: 'Email', type: 'email', required: false },
              { k: 'address', label: 'Địa chỉ', type: 'text', required: false },
            ].map(({ k, label, type, required }) => (
              <div key={k}>
                <label className="block text-sm font-medium mb-1">{label}</label>
                <input type={type} required={required}
                  value={form[k as keyof typeof form]}
                  onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))}
                  className="w-full border rounded px-3 py-2" />
              </div>
            ))}
            <div className="flex gap-3 pt-2">
              <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded">Lưu</button>
              <button type="button" onClick={() => setShowForm(false)} className="flex-1 border rounded py-2">Hủy</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3">Tên</th>
              <th className="text-left px-4 py-3">SĐT</th>
              <th className="text-right px-4 py-3">Tổng mua</th>
              <th className="text-right px-4 py-3">Số HĐ</th>
            </tr>
          </thead>
          <tbody>
            {items.map(c => (
              <tr key={c.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{c.name}</td>
                <td className="px-4 py-2">{c.phone}</td>
                <td className="px-4 py-2 text-right">{fmt(c.total_spent)} ₫</td>
                <td className="px-4 py-2 text-right">{c.total_orders}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: SupplierListPage** — `frontend/src/pages/customers/SupplierListPage.tsx`

Similar structure to CustomerListPage but for suppliers. Fields: name, phone, email, address, tax_code.

```tsx
import { useEffect, useState, useCallback } from 'react'
import { getSuppliers, createSupplier } from '../../api/customers'
import type { Supplier } from '../../types'
import toast from 'react-hot-toast'

export default function SupplierListPage() {
  const [items, setItems] = useState<Supplier[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', phone: '', email: '', address: '', tax_code: '' })

  const load = useCallback(async () => {
    try { const d = await getSuppliers(); setItems(d.items) }
    catch { toast.error('Lỗi tải NCC') }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createSupplier(form)
      toast.success('Đã thêm NCC')
      setShowForm(false)
      setForm({ name: '', phone: '', email: '', address: '', tax_code: '' })
      load()
    } catch (err: any) { toast.error(err?.response?.data?.error?.message ?? 'Lỗi') }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Nhà cung cấp</h1>
        <button onClick={() => setShowForm(true)} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          + Thêm NCC
        </button>
      </div>
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <form onSubmit={handleCreate} className="bg-white rounded-xl shadow p-6 w-96 space-y-3">
            <h2 className="font-bold text-lg">Thêm nhà cung cấp</h2>
            {[
              { k: 'name', label: 'Tên *', required: true },
              { k: 'phone', label: 'SĐT', required: false },
              { k: 'email', label: 'Email', required: false },
              { k: 'address', label: 'Địa chỉ', required: false },
              { k: 'tax_code', label: 'Mã số thuế', required: false },
            ].map(({ k, label, required }) => (
              <div key={k}>
                <label className="block text-sm font-medium mb-1">{label}</label>
                <input type="text" required={required}
                  value={form[k as keyof typeof form]}
                  onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))}
                  className="w-full border rounded px-3 py-2" />
              </div>
            ))}
            <div className="flex gap-3 pt-2">
              <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded">Lưu</button>
              <button type="button" onClick={() => setShowForm(false)} className="flex-1 border rounded py-2">Hủy</button>
            </div>
          </form>
        </div>
      )}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3">Tên</th>
              <th className="text-left px-4 py-3">SĐT</th>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-left px-4 py-3">MST</th>
            </tr>
          </thead>
          <tbody>
            {items.map(s => (
              <tr key={s.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{s.name}</td>
                <td className="px-4 py-2">{s.phone}</td>
                <td className="px-4 py-2">{s.email}</td>
                <td className="px-4 py-2">{(s as any).tax_code}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/customers/ frontend/src/api/customers.ts
git commit -m "feat: customer + supplier list pages"
```

---

## Phase 8 — Inventory Pages

### Task 10: Goods Receipt + Stock Pages

**Files:**
- Create: `frontend/src/api/inventory.ts`
- Create: `frontend/src/pages/inventory/GoodsReceiptListPage.tsx`
- Create: `frontend/src/pages/inventory/GoodsReceiptFormPage.tsx`
- Create: `frontend/src/pages/inventory/StockPage.tsx`

- [ ] **Step 1: Inventory API** — `frontend/src/api/inventory.ts`

```ts
import client from './client'

export async function getGoodsReceipts(params?: { page?: number; status?: string }) {
  const res = await client.get('/goods-receipts', { params })
  return res.data
}

export async function getGoodsReceipt(id: number) {
  const res = await client.get(`/goods-receipts/${id}`)
  return res.data
}

export async function createGoodsReceipt(data: object) {
  const res = await client.post('/goods-receipts', data)
  return res.data
}

export async function updateGoodsReceipt(id: number, data: object) {
  const res = await client.put(`/goods-receipts/${id}`, data)
  return res.data
}

export async function completeGoodsReceipt(id: number) {
  const res = await client.post(`/goods-receipts/${id}/complete`)
  return res.data
}

export async function cancelGoodsReceipt(id: number, reason?: string) {
  const res = await client.post(`/goods-receipts/${id}/cancel`, { reason })
  return res.data
}

export async function getInventory(params?: { page?: number; search?: string }) {
  const res = await client.get('/inventory', { params })
  return res.data
}

export async function getLowStock() {
  const res = await client.get('/inventory/low-stock')
  return res.data
}

export async function createAdjustment(items: Array<{ product_id: number; new_quantity: number; reason: string }>) {
  const res = await client.post('/inventory/adjustments', { items })
  return res.data
}
```

- [ ] **Step 2: GoodsReceiptListPage** — `frontend/src/pages/inventory/GoodsReceiptListPage.tsx`

```tsx
import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getGoodsReceipts, completeGoodsReceipt, cancelGoodsReceipt } from '../../api/inventory'
import type { GoodsReceipt } from '../../types'
import toast from 'react-hot-toast'

function fmt(n: number) { return new Intl.NumberFormat('vi-VN').format(Math.round(n)) }

export default function GoodsReceiptListPage() {
  const [items, setItems] = useState<GoodsReceipt[]>([])
  const [status, setStatus] = useState('')

  const load = useCallback(async () => {
    try {
      const d = await getGoodsReceipts({ page: 1, status: status || undefined })
      setItems(d.items)
    } catch { toast.error('Lỗi tải phiếu nhập') }
  }, [status])

  useEffect(() => { load() }, [load])

  const handleComplete = async (id: number) => {
    if (!confirm('Hoàn tất phiếu nhập? Tồn kho sẽ được cập nhật.')) return
    try {
      await completeGoodsReceipt(id)
      toast.success('Hoàn tất phiếu nhập!')
      load()
    } catch (err: any) { toast.error(err?.response?.data?.error?.message ?? 'Lỗi') }
  }

  const handleCancel = async (id: number) => {
    const reason = prompt('Lý do hủy:')
    if (reason === null) return
    try {
      await cancelGoodsReceipt(id, reason)
      toast.success('Đã hủy phiếu nhập')
      load()
    } catch (err: any) { toast.error(err?.response?.data?.error?.message ?? 'Lỗi') }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Phiếu nhập hàng</h1>
        <Link to="/goods-receipts/new" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          + Tạo phiếu nhập
        </Link>
      </div>
      <div className="mb-4 flex gap-2">
        {['', 'DRAFT', 'COMPLETED', 'CANCELLED'].map(s => (
          <button key={s} onClick={() => setStatus(s)}
            className={`px-3 py-1 rounded border text-sm ${status === s ? 'bg-blue-600 text-white' : 'hover:bg-gray-50'}`}>
            {s || 'Tất cả'}
          </button>
        ))}
      </div>
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3">Mã phiếu</th>
              <th className="text-right px-4 py-3">Tổng tiền</th>
              <th className="text-center px-4 py-3">Trạng thái</th>
              <th className="text-left px-4 py-3">Ngày tạo</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {items.map(r => (
              <tr key={r.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{r.code}</td>
                <td className="px-4 py-2 text-right">{fmt(r.total)} ₫</td>
                <td className="px-4 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    r.status === 'COMPLETED' ? 'bg-green-100 text-green-700'
                    : r.status === 'CANCELLED' ? 'bg-red-100 text-red-600'
                    : 'bg-yellow-100 text-yellow-700'
                  }`}>{r.status}</span>
                </td>
                <td className="px-4 py-2 text-xs text-gray-400">
                  {new Date(r.completed_at ?? '').toLocaleDateString('vi-VN')}
                </td>
                <td className="px-4 py-2 flex gap-2">
                  {r.status === 'DRAFT' && (
                    <>
                      <Link to={`/goods-receipts/${r.id}/edit`} className="text-blue-500 text-xs hover:underline">Sửa</Link>
                      <button onClick={() => handleComplete(r.id)} className="text-green-600 text-xs hover:underline">Hoàn tất</button>
                      <button onClick={() => handleCancel(r.id)} className="text-red-400 text-xs hover:underline">Hủy</button>
                    </>
                  )}
                  {r.status === 'COMPLETED' && (
                    <button onClick={() => handleCancel(r.id)} className="text-red-400 text-xs hover:underline">Hủy</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: StockPage** — `frontend/src/pages/inventory/StockPage.tsx`

```tsx
import { useEffect, useState, useCallback } from 'react'
import { getInventory, getLowStock } from '../../api/inventory'
import toast from 'react-hot-toast'

function fmt(n: number) { return new Intl.NumberFormat('vi-VN').format(Math.round(n)) }

export default function StockPage() {
  const [tab, setTab] = useState<'all' | 'low'>('all')
  const [items, setItems] = useState<any[]>([])
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    try {
      if (tab === 'low') {
        const d = await getLowStock()
        setItems(d)
      } else {
        const d = await getInventory({ page: 1, limit: 100, search: search || undefined })
        setItems(d.items)
      }
    } catch { toast.error('Lỗi tải tồn kho') }
  }, [tab, search])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Tồn kho</h1>
      <div className="mb-4 flex gap-2">
        <button onClick={() => setTab('all')} className={`px-4 py-1 rounded border text-sm ${tab === 'all' ? 'bg-blue-600 text-white' : ''}`}>Tất cả</button>
        <button onClick={() => setTab('low')} className={`px-4 py-1 rounded border text-sm ${tab === 'low' ? 'bg-red-500 text-white' : ''}`}>Sắp hết</button>
        {tab === 'all' && (
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Tìm sản phẩm..." className="border rounded px-3 py-1 ml-4 text-sm" />
        )}
      </div>
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3">SKU</th>
              <th className="text-left px-4 py-3">Tên SP</th>
              <th className="text-right px-4 py-3">Tồn kho</th>
              <th className="text-right px-4 py-3">Tối thiểu</th>
              <th className="text-right px-4 py-3">Giá vốn</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row: any) => (
              <tr key={row.product_id} className={`border-b hover:bg-gray-50 ${row.quantity <= row.min_stock && row.min_stock > 0 ? 'bg-red-50' : ''}`}>
                <td className="px-4 py-2 font-mono text-xs">{row.product_sku}</td>
                <td className="px-4 py-2">{row.product_name}</td>
                <td className="px-4 py-2 text-right font-medium">
                  {Number(row.quantity).toLocaleString('vi-VN', { maximumFractionDigits: 3 })} {row.unit}
                </td>
                <td className="px-4 py-2 text-right text-gray-400">{row.min_stock}</td>
                <td className="px-4 py-2 text-right">{fmt(row.cost_price)} ₫</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Add goods receipt form route** to App.tsx

```tsx
import GoodsReceiptFormPage from './pages/inventory/GoodsReceiptFormPage'
// in routes:
<Route path="goods-receipts/new" element={<GoodsReceiptFormPage />} />
<Route path="goods-receipts/:id/edit" element={<GoodsReceiptFormPage />} />
```

- [ ] **Step 5: GoodsReceiptFormPage** — `frontend/src/pages/inventory/GoodsReceiptFormPage.tsx`

```tsx
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createGoodsReceipt, getGoodsReceipt, updateGoodsReceipt } from '../../api/inventory'
import { searchProducts } from '../../api/products'
import { getSuppliers } from '../../api/customers'
import type { Supplier } from '../../types'
import toast from 'react-hot-toast'

interface LineItem {
  product_id: number
  product_name: string
  quantity: number
  cost_price: number
  unit_id: null
}

export default function GoodsReceiptFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [supplierId, setSupplierId] = useState<number | ''>('')
  const [items, setItems] = useState<LineItem[]>([])
  const [searchQ, setSearchQ] = useState('')
  const [searchRes, setSearchRes] = useState<any[]>([])
  const [note, setNote] = useState('')

  useEffect(() => {
    getSuppliers().then(d => setSuppliers(d.items))
    if (id) {
      getGoodsReceipt(Number(id)).then(r => {
        setSupplierId(r.supplier_id ?? '')
        setNote(r.note ?? '')
        setItems(r.items.map((i: any) => ({
          product_id: i.product_id, product_name: 'SP#' + i.product_id,
          quantity: Number(i.quantity), cost_price: Number(i.cost_price), unit_id: null,
        })))
      })
    }
  }, [id])

  const handleSearch = async (q: string) => {
    setSearchQ(q)
    if (!q.trim()) { setSearchRes([]); return }
    const d = await searchProducts(q, 8)
    setSearchRes(d.items)
  }

  const addLine = (p: any) => {
    setItems(prev => {
      const idx = prev.findIndex(i => i.product_id === p.id)
      if (idx >= 0) return prev.map((i, n) => n === idx ? { ...i, quantity: i.quantity + 1 } : i)
      return [...prev, { product_id: p.id, product_name: p.name, quantity: 1, cost_price: p.cost_price ?? 0, unit_id: null }]
    })
    setSearchQ('')
    setSearchRes([])
  }

  const total = items.reduce((s, i) => s + i.quantity * i.cost_price, 0)

  const handleSave = async () => {
    if (!items.length) { toast.error('Chưa có sản phẩm'); return }
    const body = {
      supplier_id: supplierId || null,
      note: note || null,
      paid_amount: 0,
      items: items.map(i => ({
        product_id: i.product_id,
        quantity: i.quantity,
        cost_price: i.cost_price,
        unit_id: null,
      })),
    }
    try {
      if (isEdit) {
        await updateGoodsReceipt(Number(id), body)
        toast.success('Đã cập nhật phiếu nhập')
      } else {
        await createGoodsReceipt(body)
        toast.success('Đã tạo phiếu nhập')
      }
      navigate('/goods-receipts')
    } catch (err: any) { toast.error(err?.response?.data?.error?.message ?? 'Lỗi') }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-bold mb-4">{isEdit ? 'Sửa phiếu nhập' : 'Tạo phiếu nhập'}</h1>
      <div className="bg-white rounded-xl shadow p-5 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nhà cung cấp</label>
            <select value={supplierId} onChange={e => setSupplierId(Number(e.target.value) || '')} className="w-full border rounded px-3 py-2">
              <option value="">-- Không chọn --</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Ghi chú</label>
            <input value={note} onChange={e => setNote(e.target.value)} className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        {/* Product search */}
        <div className="relative">
          <input value={searchQ} onChange={e => handleSearch(e.target.value)}
            placeholder="Tìm sản phẩm để thêm..." className="w-full border rounded px-3 py-2" />
          {searchRes.length > 0 && (
            <div className="absolute left-0 right-0 top-full mt-1 bg-white border rounded shadow z-10 max-h-48 overflow-y-auto">
              {searchRes.map((p: any) => (
                <button key={p.id} onClick={() => addLine(p)} className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b text-sm">
                  {p.name} — {p.sku}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Line items */}
        {items.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2">Sản phẩm</th>
                <th className="text-right px-3 py-2 w-28">Số lượng</th>
                <th className="text-right px-3 py-2 w-32">Giá nhập</th>
                <th className="text-right px-3 py-2 w-28">Thành tiền</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx} className="border-b">
                  <td className="px-3 py-1">{item.product_name}</td>
                  <td className="px-3 py-1">
                    <input type="number" min={0.001} step={0.001} value={item.quantity}
                      onChange={e => setItems(prev => prev.map((i, n) => n === idx ? { ...i, quantity: Number(e.target.value) } : i))}
                      className="w-full border rounded px-2 py-0.5 text-right" />
                  </td>
                  <td className="px-3 py-1">
                    <input type="number" min={0} value={item.cost_price}
                      onChange={e => setItems(prev => prev.map((i, n) => n === idx ? { ...i, cost_price: Number(e.target.value) } : i))}
                      className="w-full border rounded px-2 py-0.5 text-right" />
                  </td>
                  <td className="px-3 py-1 text-right">{new Intl.NumberFormat('vi-VN').format(item.quantity * item.cost_price)}</td>
                  <td className="px-3 py-1">
                    <button onClick={() => setItems(prev => prev.filter((_, n) => n !== idx))} className="text-red-400 text-xs">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="font-bold">
                <td colSpan={3} className="px-3 py-2 text-right">Tổng:</td>
                <td className="px-3 py-2 text-right">{new Intl.NumberFormat('vi-VN').format(total)} ₫</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        )}

        <div className="flex gap-3 pt-2">
          <button onClick={handleSave} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">Lưu nháp</button>
          <button onClick={() => navigate('/goods-receipts')} className="border px-6 py-2 rounded hover:bg-gray-50">Hủy</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/inventory/ frontend/src/api/inventory.ts
git commit -m "feat: goods receipt + stock inventory pages"
```

---

## Phase 9 — Reports

### Task 11: Revenue Report Page

**Files:**
- Modify: `frontend/src/pages/reports/RevenuePage.tsx`

- [ ] **Step 1: RevenuePage with chart** — `frontend/src/pages/reports/RevenuePage.tsx`

```tsx
import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getRevenue } from '../../api/reports'
import toast from 'react-hot-toast'

function fmt(n: number) { return new Intl.NumberFormat('vi-VN').format(Math.round(n)) }

function todayStr() { return new Date().toISOString().slice(0, 10) }
function weekAgoStr() {
  const d = new Date(); d.setDate(d.getDate() - 6); return d.toISOString().slice(0, 10)
}

export default function RevenuePage() {
  const [from, setFrom] = useState(weekAgoStr())
  const [to, setTo] = useState(todayStr())
  const [groupBy, setGroupBy] = useState('day')
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    getRevenue({ from, to, group_by: groupBy })
      .then(setData)
      .catch(() => toast.error('Lỗi tải báo cáo'))
  }, [from, to, groupBy])

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Báo cáo doanh thu</h1>
      <div className="flex gap-3 mb-6 items-center">
        <input type="date" value={from} onChange={e => setFrom(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <span>đến</span>
        <input type="date" value={to} onChange={e => setTo(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <select value={groupBy} onChange={e => setGroupBy(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="day">Theo ngày</option>
          <option value="month">Theo tháng</option>
        </select>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl shadow p-4">
              <div className="text-sm text-gray-500">Doanh thu</div>
              <div className="text-2xl font-bold">{fmt(data.total_revenue)} ₫</div>
            </div>
            <div className="bg-white rounded-xl shadow p-4">
              <div className="text-sm text-gray-500">Lợi nhuận</div>
              <div className="text-2xl font-bold text-green-600">{fmt(data.total_profit)} ₫</div>
            </div>
            <div className="bg-white rounded-xl shadow p-4">
              <div className="text-sm text-gray-500">Số hóa đơn</div>
              <div className="text-2xl font-bold">{data.total_invoices}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow p-5">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.series} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={v => fmt(v)} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => fmt(v) + ' ₫'} />
                <Bar dataKey="revenue" fill="#3b82f6" name="Doanh thu" />
                <Bar dataKey="profit" fill="#10b981" name="Lợi nhuận" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/reports/
git commit -m "feat: revenue report page with bar chart"
```

---

## Phase 10 — Deployment Setup

### Task 12: Nginx + Production Config

**Files:**
- Create: `nginx.conf`
- Create: `.env.example`
- Modify: `docker-compose.yml` (add frontend build service)

- [ ] **Step 1: Create .env.example**

```bash
cat > /Users/vuongnv/Documents/my_kiot/.env.example << 'EOF'
DATABASE_URL=postgresql+asyncpg://pos_user:pos_secret@localhost:5432/pos_db
JWT_SECRET_KEY=CHANGE_ME_64_CHAR_RANDOM_STRING_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12
APP_ENV=production
CORS_ORIGINS=https://your-domain.com
EOF
```

- [ ] **Step 2: Create nginx.conf**

```nginx
# nginx.conf
server {
    listen 80;
    server_name _;

    # Serve React frontend
    root /var/www/pos/dist;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

- [ ] **Step 3: Add build script to package.json** — already handled by Vite default `npm run build`

- [ ] **Step 4: Create a deployment README** — `docs/deploy.md`

Document:
1. `docker compose up -d db`
2. `pip install -r backend/requirements.txt`
3. `alembic upgrade head`
4. `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4`
5. `cd frontend && npm run build && cp -r dist /var/www/pos/`
6. `sudo systemctl restart nginx`

- [ ] **Step 5: Commit**

```bash
git add .env.example nginx.conf docs/deploy.md
git commit -m "feat: nginx config + deployment docs"
```

---

## Self-Review

### Spec Coverage Check

| Feature | Task |
|---------|------|
| Python 3.9 compat fix | Task 1 |
| Frontend setup (Vite + React + Tailwind) | Task 2 |
| Auth store + axios interceptor (auto-refresh) | Task 3 |
| Router + layout (Sidebar, Header, route guard) | Task 4 |
| Login / Register pages | Task 5 |
| Dashboard with stat cards | Task 6 |
| Product list + create/edit form | Task 7 |
| POS screen (barcode scan, cart, payment) | Task 8 |
| Invoice history + cancel | Task 8 |
| Customer list + create modal | Task 9 |
| Supplier list + create modal | Task 9 |
| Goods receipt list + complete/cancel | Task 10 |
| Goods receipt form (create/edit) | Task 10 |
| Inventory / stock view + low-stock filter | Task 10 |
| Revenue report + bar chart | Task 11 |
| Nginx config + deployment docs | Task 12 |

### Known gaps (defer to next iteration):
- Category management page (CategoryPage.tsx) — placeholder remains
- Product units management UI
- Stock adjustment UI (AdjustmentPage)
- Top products + profit report pages
- Staff management page (OWNER only)
- Token restore on page refresh (currently access token lost on reload — needs `getMe()` call on app init using stored refresh token)
