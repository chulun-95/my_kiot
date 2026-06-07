# Token restore bản bảo mật (HttpOnly cookie) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Access token chỉ giữ trong memory; refresh token chuyển sang **HttpOnly cookie** (JS không đọc được → chống XSS); khôi phục phiên khi mở app bằng 1 lần `/auth/refresh` (cookie tự gửi), có splash khi đang khôi phục.

**Architecture:** Backend set/đọc/xóa refresh token qua HttpOnly cookie (`Secure` theo env, `SameSite=Strict`, `Path=/api/v1/auth`); **loại `refresh_token` khỏi mọi response body** bằng `response_model_exclude`. Frontend bỏ persist token vào localStorage, access token + user/tenant chỉ ở memory; App bootstrap gọi refresh lúc mount, hiện splash tới khi xong.

**Tech Stack:** FastAPI, Pydantic v2, pytest (SQLite, httpx — tự quản cookie), React 18 + TS + Zustand + Vitest + MSW.

**Quyết định đã chốt (Gate 1):** access token memory-only; refresh token HttpOnly cookie; bootstrap có **splash "Đang tải..."**; KHÔNG persist gì nhạy cảm; `COOKIE_SECURE` theo env. Chấp nhận user đang đăng nhập bị **logout 1 lần** sau deploy. CSRF dựa `SameSite=Strict` + header `X-Requested-With`.

---

### Task 1: Backend — config + cookie helper

**Files:**
- Modify: `backend/config.py`
- Create: `backend/modules/auth/cookies.py`

- [ ] **Step 1: Thêm setting `COOKIE_SECURE`** vào `backend/config.py` (sau `CORS_ORIGINS`, dòng 24):

```python
    COOKIE_SECURE: bool = False  # True ở production (HTTPS); dev/HTTP để False
```

- [ ] **Step 2: Tạo `backend/modules/auth/cookies.py`**

```python
from fastapi import Response

from backend.config import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _max_age_seconds() -> int:
    return settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=_max_age_seconds(),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
```

- [ ] **Step 3: Verify import** — Run: `python -c "import backend.modules.auth.cookies"` → exit 0.

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/modules/auth/cookies.py
git commit -m "feat(auth): COOKIE_SECURE setting + refresh cookie helpers"
```

---

### Task 2: Backend — router cookie integration

**Files:**
- Modify: `backend/modules/auth/router.py`

Mục tiêu: set refresh cookie ở register/login/refresh/change-password; đọc cookie ở refresh/logout; xóa cookie ở logout; **loại `refresh_token` khỏi mọi body** bằng `response_model_exclude`.

- [ ] **Step 1: Cập nhật imports** — đầu `backend/modules/auth/router.py`:

```python
from typing import Annotated, Union

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.exceptions import AppError
from backend.modules.auth import service as auth_service
from backend.modules.auth.cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from backend.modules.auth.models import User
from backend.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginSuccessResponse,
    LoginTenantSelectionResponse,
    MeResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    TenantBrief,
    TokenPair,
    UserBrief,
)
```

(Đã bỏ `RefreshRequest`, `LogoutRequest` khỏi import — không còn dùng.)

- [ ] **Step 2: register** — thay endpoint:

```python
@router.post(
    "/register",
    response_model=RegisterResponse,
    response_model_exclude={"refresh_token"},
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await auth_service.register(db, payload)
    set_refresh_cookie(response, result.refresh_token)
    return result
```

- [ ] **Step 3: login** — thay endpoint:

```python
@router.post(
    "/login",
    response_model=Union[LoginSuccessResponse, LoginTenantSelectionResponse],
    response_model_exclude={"refresh_token"},
)
@limiter.limit("5/5minute")
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await auth_service.login(db, payload)
    if isinstance(result, LoginSuccessResponse):
        set_refresh_cookie(response, result.refresh_token)
    return result
```

- [ ] **Step 4: refresh** — đọc cookie, không còn body:

```python
@router.post(
    "/refresh",
    response_model=LoginSuccessResponse,
    response_model_exclude={"refresh_token"},
)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
):
    if not refresh_token:
        raise AppError(401, "MISSING_REFRESH_TOKEN", "Phiên đăng nhập đã hết hạn")
    result = await auth_service.refresh_tokens(db, refresh_token)
    set_refresh_cookie(response, result.refresh_token)
    return result
```

- [ ] **Step 5: logout** — đọc cookie + xóa cookie:

```python
@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
):
    if refresh_token:
        await auth_service.logout(db, user.id, refresh_token)
    clear_refresh_cookie(response)
    return MessageResponse(message="Đăng xuất thành công")
```

- [ ] **Step 6: change-password** — set cookie mới, body chỉ access:

```python
@router.put(
    "/change-password",
    response_model=TokenPair,
    response_model_exclude={"refresh_token"},
)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    access, refresh_value = await auth_service.change_password(db, user, payload)
    set_refresh_cookie(response, refresh_value)
    return TokenPair(access_token=access, refresh_token=refresh_value)
```

(`/me` giữ nguyên.)

- [ ] **Step 7: Smoke check import** — Run: `python -c "import backend.main"` → exit 0.

- [ ] **Step 8: Commit**

```bash
git add backend/modules/auth/router.py
git commit -m "feat(auth): refresh token via HttpOnly cookie; drop from response body"
```

---

### Task 3: Backend — migrate auth tests + fixture

**Files:**
- Modify: `tests/conftest.py` (fixture `registered_owner`)
- Modify: `tests/test_auth.py`

> httpx `AsyncClient` tự lưu cookie từ `Set-Cookie` và tự gửi lại trên cùng client. `resp.cookies.get("refresh_token")` đọc giá trị cookie server set. Truyền cookie thủ công 1 request: `client.post(url, cookies={"refresh_token": old})`.

- [ ] **Step 1: Cập nhật `registered_owner`** trong `tests/conftest.py` — thêm dòng lấy refresh từ cookie (sau `data = resp.json()`):

```python
    data = resp.json()
    data["refresh_token"] = resp.cookies.get("refresh_token")
    data["password"] = payload["password"]
    data["phone"] = payload["phone"]
    return data
```

- [ ] **Step 2: Sửa assert "refresh_token in body" → cookie** trong `tests/test_auth.py`.
  - Dòng ~21 (sau register) và ~114 (sau login): đổi `assert "refresh_token" in data` thành:

```python
    assert "refresh_token" not in data
    assert resp.cookies.get("refresh_token")
```

(Đặt đúng biến `resp`/`data` của từng test — đọc context quanh dòng đó; tên biến response có thể là `resp` hoặc `r`.)

- [ ] **Step 3: Thay test logout** (`test_logout_invalidates_refresh_token`):

```python
@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(client, registered_owner):
    old = registered_owner["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {registered_owner['access_token']}"},
    )
    assert resp.status_code == 200

    r = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old})
    assert r.status_code == 401
```

- [ ] **Step 4: Thay test refresh rotation** (`test_refresh_rotates_tokens`):

```python
@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client, registered_owner):
    old_refresh = registered_owner["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert r.status_code == 200
    new_refresh = r.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh
    assert "refresh_token" not in r.json()

    # tái sử dụng token cũ → bị từ chối (reuse detection)
    r2 = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert r2.status_code == 401
```

- [ ] **Step 5: Thay test change-password invalidation** (`test_change_password_invalidates_old_refresh_tokens`):

```python
@pytest.mark.asyncio
async def test_change_password_invalidates_old_refresh_tokens(client, registered_owner):
    old_refresh = registered_owner["refresh_token"]
    headers = {"Authorization": f"Bearer {registered_owner['access_token']}"}
    r = await client.put(
        "/api/v1/auth/change-password",
        json={
            "current_password": registered_owner["password"],
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
        headers=headers,
    )
    assert r.status_code == 200
    assert "refresh_token" not in r.json()

    r2 = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert r2.status_code == 401
```

(Các test change-password khác chỉ assert `access_token` / status — giữ nguyên.)

- [ ] **Step 6: Run auth tests** — Run: `python -m pytest tests/test_auth.py -q`
Expected: tất cả PASS. (Nếu 1 test còn đọc `data["refresh_token"]` ở body → sửa nốt theo pattern Step 2.)

- [ ] **Step 7: Run full backend suite** — Run: `python -m pytest tests/ -q` → all pass (các test khác dùng `registered_owner["access_token"]` không đổi).

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py tests/test_auth.py
git commit -m "test(auth): migrate refresh/logout tests to cookie-based flow"
```

---

### Task 4: Frontend — authStore (memory-only + bootstrap)

**Files:**
- Modify: `frontend/src/stores/authStore.ts`

- [ ] **Step 1: Viết lại store** (bỏ `refreshToken`, bỏ `persist`, thêm `initializing` + `bootstrap`):

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
  initializing: boolean;
  setAuth: (payload: { user: User; tenant: Tenant; accessToken: string }) => void;
  setUser: (user: User) => void;
  setAccessToken: (token: string | null) => void;
  logout: () => void;
  bootstrap: () => Promise<void>;
  login: (phone: string, password: string, tenantId?: number) => Promise<LoginPendingSelection | null>;
  register: (payload: authApi.RegisterPayload) => Promise<void>;
  doLogout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  tenant: null,
  accessToken: null,
  initializing: true,
  setAuth: ({ user, tenant, accessToken }) => set({ user, tenant, accessToken }),
  setUser: (user) => set({ user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  logout: () => set({ user: null, tenant: null, accessToken: null }),
  bootstrap: async () => {
    try {
      const res = await authApi.refresh();
      set({
        user: res.user,
        tenant: res.tenant,
        accessToken: res.access_token,
        initializing: false,
      });
    } catch {
      set({ user: null, tenant: null, accessToken: null, initializing: false });
    }
  },
  login: async (phone, password, tenantId) => {
    const res = await authApi.login({ phone, password, tenant_id: tenantId });
    if ('requires_tenant_selection' in res && res.requires_tenant_selection) {
      return res;
    }
    const success = res as authApi.LoginSuccess;
    set({ user: success.user, tenant: success.tenant, accessToken: success.access_token });
    return null;
  },
  register: async (payload) => {
    const res = await authApi.register(payload);
    set({ user: res.user, tenant: res.tenant, accessToken: res.access_token });
  },
  doLogout: async () => {
    try {
      await authApi.logout();
    } catch {
      // swallow — luôn xóa state local
    }
    set({ user: null, tenant: null, accessToken: null });
  },
}));
```

- [ ] **Step 2: Verify tsc** — sẽ còn lỗi ở `api/auth.ts` (chữ ký `refresh`/`logout` cũ) và `client.ts` (`setTokens`) — sửa ở Task 5. Tạm bỏ qua, không commit lẻ. (Có thể chạy `cd frontend && npx tsc --noEmit` để thấy danh sách lỗi sẽ fix ở Task 5.)

---

### Task 5: Frontend — api/auth.ts + client.ts (cookie-based)

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: `api/auth.ts`** — `refresh()` không tham số, `logout()` không tham số; `LoginSuccess.refresh_token` thành optional:

Thay `refresh` và `logout`:

```typescript
export async function refresh(): Promise<LoginSuccess> {
  const { data } = await apiClient.post<LoginSuccess>('/auth/refresh', {});
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout', {});
}
```

Và sửa interface `LoginSuccess` (refresh_token không còn được trả) — đổi field thành optional để tương thích:

```typescript
export interface LoginSuccess {
  user: User;
  tenant: Tenant;
  access_token: string;
  refresh_token?: string;
}
```

(`TokenPair`, `RegisterPayload`... giữ nguyên; `refresh_token` optional là đủ.)

- [ ] **Step 2: `client.ts`** — `refreshAccessToken` không đọc rt từ store, POST body rỗng (cookie tự gửi):

Thay block `refreshAccessToken`:

```typescript
let refreshPromise: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const res = await axios.post(
        `${baseURL}/auth/refresh`,
        {},
        { withCredentials: true, headers: { 'X-Requested-With': 'XMLHttpRequest' } },
      );
      const newAccess = (res.data?.access_token as string) || null;
      if (newAccess) {
        useAuthStore.getState().setAccessToken(newAccess);
      }
      return newAccess;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}
```

(Phần request interceptor + response interceptor 401 giữ nguyên — chúng gọi `refreshAccessToken()` và `logout()`/redirect như cũ.)

- [ ] **Step 3: Grep dọn tham chiếu cũ** — Run: `cd frontend && grep -rn "refreshToken\|setTokens" src` (loại trừ file test sẽ xử lý ở Task 7). Sửa mọi chỗ còn dùng `refreshToken`/`setTokens` (ví dụ `ChangePassword.tsx` nếu có gọi `setTokens` → đổi sang `setAccessToken` với `res.access_token`).

- [ ] **Step 4: Verify tsc** — Run: `cd frontend && npx tsc --noEmit` → exit 0 (trừ test files sẽ fix ở Task 7 nếu chúng còn tham chiếu refreshToken; nếu tsc tính cả test, fix ngay phần test ở Task 7 trước khi commit chung).

- [ ] **Step 5: Commit (Task 4+5 chung khi tsc sạch)**

```bash
git add frontend/src/stores/authStore.ts frontend/src/api/auth.ts frontend/src/api/client.ts
git commit -m "feat(auth-fe): access token in memory, cookie-based refresh, bootstrap action"
```

---

### Task 6: Frontend — App bootstrap splash + ProtectedRoute

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Thêm bootstrap + splash** — trong `App.tsx`, thêm import `useEffect` và store, và gate `initializing`:

Ở đầu component `App()` (trước `return`):

```tsx
  const initializing = useAuthStore((s) => s.initializing);
  const bootstrap = useAuthStore((s) => s.bootstrap);
  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  if (initializing) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-500">
        Đang tải...
      </div>
    );
  }
```

Thêm imports cần thiết ở đầu file nếu chưa có:

```tsx
import { useEffect } from 'react';
import { useAuthStore } from './stores/authStore';
```

(`ProtectedRoute` giữ nguyên — vì App chỉ render routes sau khi `initializing=false`, nên `accessToken` đã ổn định, không nháy về /login.)

- [ ] **Step 2: Verify tsc** — Run: `cd frontend && npx tsc --noEmit` → exit 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(auth-fe): bootstrap session on app load with loading splash"
```

---

### Task 7: Frontend — migrate auth tests + MSW

**Files:**
- Modify: `frontend/src/stores/__tests__/authStore.test.ts`
- Modify: `frontend/src/__tests__/mocks/handlers.ts` (đảm bảo có handler `*/auth/refresh`)

- [ ] **Step 1: Đảm bảo MSW có handler refresh** — grep `frontend/src/__tests__/mocks/handlers.ts` cho `auth/refresh`. Nếu CHƯA có, thêm:

```typescript
  http.post('*/auth/refresh', () =>
    HttpResponse.json({
      user: { id: 1, full_name: 'Owner A', role: 'OWNER' },
      tenant: { id: 1, name: 'Shop A', slug: 'shop-a' },
      access_token: 'access-1',
    }),
  ),
```

(Nếu đã có nhưng trả `refresh_token`, để nguyên cũng được — FE bỏ qua field đó.)

- [ ] **Step 2: Sửa `authStore.test.ts`** — bỏ mọi `refreshToken`:

```typescript
import { beforeEach, describe, expect, it } from 'vitest';
import { useAuthStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, tenant: null, accessToken: null });
  });

  it('starts empty', () => {
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.tenant).toBeNull();
    expect(s.accessToken).toBeNull();
  });

  it('login action sets user/tenant/access token via API', async () => {
    const res = await useAuthStore.getState().login('0900000001', 'secret123');
    expect(res).toBeNull();
    const s = useAuthStore.getState();
    expect(s.user?.id).toBe(1);
    expect(s.tenant?.slug).toBe('shop-a');
    expect(s.accessToken).toBe('access-1');
  });

  it('bootstrap restores session from refresh cookie', async () => {
    await useAuthStore.getState().bootstrap();
    const s = useAuthStore.getState();
    expect(s.accessToken).toBe('access-1');
    expect(s.user?.id).toBe(1);
    expect(s.initializing).toBe(false);
  });

  it('doLogout clears state', async () => {
    useAuthStore.setState({
      user: { id: 1, full_name: 'X', role: 'OWNER' },
      tenant: { id: 1, name: 'Y', slug: 'y' },
      accessToken: 'a',
    });
    await useAuthStore.getState().doLogout();
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.accessToken).toBeNull();
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

- [ ] **Step 3: Run liên quan + full FE suite** — Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: tsc exit 0; toàn bộ test pass. Nếu test nào (Login/Register/ChangePassword) còn assert `refreshToken` hoặc localStorage token → sửa theo hướng bỏ refresh token (đọc lỗi cụ thể, cập nhật assertion).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/__tests__/authStore.test.ts frontend/src/__tests__/mocks/handlers.ts
git commit -m "test(auth-fe): migrate store tests to memory token + bootstrap"
```

---

### Task 8: Verify toàn hệ thống

- [ ] **Step 1: Backend** — Run: `python -m pytest tests/ -q` → all pass.
- [ ] **Step 2: Frontend** — Run: `cd frontend && npx tsc --noEmit && npx vitest run` → tsc exit 0; all pass.
- [ ] **Step 3: Commit (nếu còn)** — `git add -A && git commit -m "chore(auth): secure token restore complete" || echo nothing`

---

## Self-Review

**1. Spec coverage:** access token memory-only (Task 4 store bỏ persist) ✅; refresh token HttpOnly cookie (Task 1,2) ✅; loại refresh_token khỏi body (Task 2 `response_model_exclude`) ✅; bootstrap restore + splash (Task 6) ✅; refresh/logout đọc cookie (Task 2) ✅; COOKIE_SECURE theo env (Task 1) ✅; SameSite=Strict + X-Requested-With (Task 1 + client.ts giữ header) ✅; tiếng Việt message (Task 2 AppError, Task 6 splash) ✅.

**2. Pattern dự án / Migration checklist:** không có bảng mới → không cần migration/alembic ✅; không mutation nghiệp vụ → không cần audit mới ✅; rotation/reuse-detection giữ nguyên ở service (không đụng) ✅; tenant isolation không liên quan (auth) ✅.

**3. Placeholder scan:** không TODO/placeholder. Mọi step có code + lệnh + expected.

**4. Type/contract consistency:** `authApi.refresh()`/`logout()` đổi chữ ký → store (Task 4) + client (Task 5) + tests (Task 7) đồng bộ. `LoginSuccess.refresh_token` optional. `setTokens`/`refreshToken` bị loại — Task 5 Step 3 grep dọn tham chiếu còn sót. `response_model_exclude={"refresh_token"}` áp cho register/login/refresh/change-password.

**Rủi ro & lưu ý implementer:**
- `response_model_exclude` trên union (login): nhánh selection không có field refresh_token → exclude là no-op, an toàn. Test Task 3 xác nhận body không có refresh_token.
- httpx test: cookie tự quản trên cùng `client`; reuse-test phải truyền `cookies={...}` thủ công.
- Sau deploy: user cũ bị logout 1 lần (đã thông báo, chấp nhận).
- Dev HTTP: `COOKIE_SECURE=False` để cookie gửi được; prod đặt `COOKIE_SECURE=true` trong `.env`.
- Nếu tsc/test FE còn file khác tham chiếu `refreshToken` (Login/Register/ChangePassword .tsx hoặc test), sửa theo cùng nguyên tắc — Task 5 Step 3 + Task 7 Step 3 đã yêu cầu grep & fix.
