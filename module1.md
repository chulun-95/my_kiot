# CLAUDE.md — POS System (Hệ thống quản lý bán hàng)

## Dự án là gì

Hệ thống POS + quản lý kho cho tạp hóa/siêu thị mini (giống KiotViet). Multi-tenant SaaS — mỗi shop = 1 tenant.

## Tech stack

- Backend: Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / Alembic
- Database: PostgreSQL 16
- Frontend: React 18 + Vite + TypeScript + Tailwind CSS + Zustand
- Auth: JWT (HS256) + bcrypt + refresh token
- Không dùng Redis/Queue ở giai đoạn này

## Cấu trúc project

```
pos-system/
├── CLAUDE.md                       ← file này
├── docker-compose.yml
├── .env.example
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── backend/
│   ├── main.py                     # FastAPI app, mount routers
│   ├── config.py                   # pydantic Settings từ .env
│   ├── database.py                 # async engine + sessionmaker
│   ├── dependencies.py             # get_db, get_current_user, require_role
│   ├── exceptions.py               # custom HTTPException handlers
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── router.py
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py           # User, RefreshToken
│   │   │   └── utils.py            # hash_password, verify_password, create_jwt, create_refresh_token
│   │   └── tenant/
│   │       ├── router.py
│   │       ├── service.py
│   │       ├── schemas.py
│   │       └── models.py           # Tenant
│   └── shared/
│       ├── models.py               # Base, AuditMixin, TenantMixin
│       └── pagination.py           # paginate helper
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts           # axios instance + interceptor
│       ├── stores/authStore.ts     # zustand
│       ├── pages/auth/
│       │   ├── LoginPage.tsx
│       │   └── RegisterPage.tsx
│       ├── pages/staff/StaffPage.tsx
│       ├── components/layout/
│       │   ├── Sidebar.tsx
│       │   └── Header.tsx
│       └── components/shared/
└── tests/
    ├── conftest.py
    └── test_auth.py
```

## Lệnh chạy

```bash
# Database
docker compose up -d db

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Test
cd backend && pytest tests/ -v
```

---

# MODULE HIỆN TẠI: AUTH & TENANT (UC-A)

Module nền tảng. Mọi module khác phụ thuộc vào `get_current_user` và `tenant_id` từ module này.

## Database — 3 bảng

### tenants

```sql
CREATE TABLE tenants (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    email           VARCHAR(200),
    address         TEXT,
    settings        JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### users

```sql
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    phone           VARCHAR(20),
    email           VARCHAR(200),
    full_name       VARCHAR(200) NOT NULL,
    password_hash   VARCHAR(200) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'CASHIER',  -- OWNER | CASHIER
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, phone),
    UNIQUE (tenant_id, email)
);
CREATE INDEX idx_users_tenant ON users(tenant_id);
```

### refresh_tokens

```sql
CREATE TABLE refresh_tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(500) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at);
```

## API Endpoints — 11 endpoints

### Public (không cần token)

```
POST /api/v1/auth/register       → Tạo tenant + user OWNER + trả tokens
POST /api/v1/auth/login          → Xác thực SĐT + password → trả tokens
POST /api/v1/auth/refresh        → Gia hạn access token bằng refresh token
```

### Authenticated (cần Bearer token)

```
POST /api/v1/auth/logout              → Xóa refresh token khỏi DB
PUT  /api/v1/auth/change-password     → Đổi mật khẩu (cần MK cũ)
GET  /api/v1/auth/me                  → Trả thông tin user + tenant hiện tại
```

### Owner only (cần role = OWNER)

```
GET    /api/v1/staff                  → Danh sách nhân viên (phân trang)
POST   /api/v1/staff                  → Tạo nhân viên CASHIER mới
PUT    /api/v1/staff/{id}             → Sửa thông tin nhân viên
PATCH  /api/v1/staff/{id}/deactivate  → Khóa nhân viên
PATCH  /api/v1/staff/{id}/activate    → Mở khóa nhân viên
```

## Chi tiết business logic từng endpoint

### POST /api/v1/auth/register

Request:
```json
{
    "shop_name": "Tạp hóa Minh Anh",
    "owner_name": "Nguyễn Minh Anh",
    "phone": "0901234567",
    "email": "minhanh@gmail.com",   // optional
    "password": "123456"
}
```

Logic:
1. Validate: phone regex VN `^(0[3|5|7|8|9])[0-9]{8}$`, password >= 6 chars, shop_name 2-200 chars
2. Check phone chưa tồn tại ở BẤT KỲ tenant nào (vì lúc đăng ký chưa có tenant): `SELECT FROM users WHERE phone = :phone AND deleted_at IS NULL` → 409 nếu có
3. Sinh slug từ shop_name: "Tạp hóa Minh Anh" → "tap-hoa-minh-anh". Nếu trùng → thêm 4 hex random
4. BEGIN TRANSACTION: INSERT tenant → hash password bcrypt(cost=12) → INSERT user(role='OWNER') → COMMIT
5. Tạo JWT access_token (60 phút) payload: `{"sub": user_id, "tid": tenant_id, "role": "OWNER"}`
6. Tạo refresh_token (random 64 chars), lưu DB (expire 30 ngày)
7. Trả 201

Response 201:
```json
{
    "tenant": {"id": 1, "name": "Tạp hóa Minh Anh", "slug": "tap-hoa-minh-anh"},
    "user": {"id": 1, "full_name": "Nguyễn Minh Anh", "phone": "0901234567", "role": "OWNER"},
    "access_token": "eyJ...",
    "refresh_token": "a1b2c3...",
    "token_type": "Bearer"
}
```

Errors: 409 PHONE_EXISTS, 422 validation

### POST /api/v1/auth/login

Request:
```json
{
    "phone": "0901234567",
    "password": "123456",
    "tenant_id": null  // optional, chỉ khi SĐT thuộc nhiều tenant
}
```

Logic:
1. `SELECT FROM users WHERE phone = :phone AND deleted_at IS NULL`
2. 0 results → 401 "Số điện thoại hoặc mật khẩu không đúng"
3. Nhiều results VÀ không có tenant_id → trả 200 với `requires_tenant_selection: true` + danh sách tenants
4. 1 result HOẶC có tenant_id → verify bcrypt → sai: 401 (message GIỐNG khi SĐT không tồn tại)
5. Check user.is_active → false: 403 "Tài khoản đã bị khóa"
6. Check tenant.is_active → false: 403 "Shop đã bị tạm ngưng"
7. Tạo tokens, update last_login_at, trả 200

Response khi multi-tenant (200):
```json
{
    "requires_tenant_selection": true,
    "tenants": [
        {"id": 1, "name": "Tạp hóa Minh Anh", "role": "OWNER"},
        {"id": 5, "name": "Siêu thị Mini ABC", "role": "CASHIER"}
    ]
}
```

Response thành công (200):
```json
{
    "user": {"id": 1, "full_name": "...", "phone": "...", "email": "...", "role": "OWNER"},
    "tenant": {"id": 1, "name": "...", "slug": "..."},
    "access_token": "eyJ...",
    "refresh_token": "...",
    "token_type": "Bearer"
}
```

### POST /api/v1/auth/refresh

Request: `{"refresh_token": "a1b2c3..."}`

Logic:
1. Tìm token trong DB → 401 nếu không thấy
2. Check expires_at > now → 401 nếu hết hạn, xóa token
3. Tìm user → check is_active + tenant.is_active → 401 nếu bị khóa
4. Tạo access_token mới + refresh_token mới (rotation), xóa token cũ
5. Trả 200

### POST /api/v1/auth/logout

Header: `Authorization: Bearer {access_token}`
Request: `{"refresh_token": "a1b2c3..."}`

Logic: DELETE FROM refresh_tokens WHERE token = :token AND user_id = :current_user_id → trả 200

### PUT /api/v1/auth/change-password

Request:
```json
{
    "current_password": "123456",
    "new_password": "newpass123",
    "confirm_password": "newpass123"
}
```

Logic:
1. Verify current_password → sai: 400
2. new_password >= 6 chars, != current_password, == confirm_password
3. Hash + UPDATE password_hash
4. DELETE ALL refresh_tokens of this user (force re-login everywhere)
5. Tạo refresh_token mới cho session hiện tại
6. Trả 200 với tokens mới

### GET /api/v1/auth/me

Trả thông tin user + tenant hiện tại từ JWT. Không query DB nếu không cần.

### POST /api/v1/staff (Owner only)

Request:
```json
{
    "full_name": "Trần Văn B",
    "phone": "0987654321",
    "email": null,
    "password": "123456"
}
```

Logic:
1. Check current_user.role == 'OWNER' → 403
2. Check phone unique trong tenant → 409
3. Hash password, INSERT user(role='CASHIER', tenant_id = current_user.tenant_id)
4. Trả 201

### GET /api/v1/staff (Owner only)

Query params: `?page=1&limit=20&search=abc&is_active=true`

Logic: SELECT FROM users WHERE tenant_id = :tid AND deleted_at IS NULL + filters + pagination
Response: `{"items": [...], "pagination": {"page": 1, "limit": 20, "total": 5, "total_pages": 1}}`

KHÔNG trả password_hash trong response.

### PATCH /api/v1/staff/{id}/deactivate (Owner only)

Logic:
1. Tìm user by id + tenant_id → 404
2. Check id != current_user.id → 400 "Không thể khóa chính mình"
3. SET is_active = FALSE
4. DELETE all refresh_tokens of this user
5. Trả 200

### PATCH /api/v1/staff/{id}/activate (Owner only)

Logic: SET is_active = TRUE → trả 200

## Shared code patterns (BẮT BUỘC tuân thủ)

### Dependencies (backend/dependencies.py)

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

security = HTTPBearer()

async def get_db():
    async with async_session() as session:
        yield session

async def get_current_user(
    token=Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token không hợp lệ")
    
    user = await db.get(User, payload["sub"])
    if not user or user.deleted_at or not user.is_active:
        raise HTTPException(401, "Tài khoản không hợp lệ")
    
    # Gắn tenant_id vào user object để dùng ở mọi nơi
    user.current_tenant_id = payload["tid"]
    return user

def require_role(*roles):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Bạn không có quyền thực hiện")
        return user
    return checker
```

### Response format chuẩn

Thành công:
```json
{"items": [...], "pagination": {...}}   // list
{"id": 1, "name": "..."}               // single
{"message": "Thành công"}              // action
```

Lỗi:
```json
{
    "error": {
        "code": "PHONE_EXISTS",
        "message": "Số điện thoại đã được đăng ký",
        "details": {}
    }
}
```

### Pagination helper

```python
async def paginate(db, stmt, page=1, limit=20):
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
    
    items = (await db.execute(
        stmt.offset((page - 1) * limit).limit(limit)
    )).scalars().all()
    
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": ceil(total / limit)
        }
    }
```

### Tenant isolation — QUY TẮC VÀNG

Mọi query PHẢI filter theo tenant_id từ JWT:
```python
# ĐÚNG
stmt = select(User).where(User.tenant_id == current_user.current_tenant_id)

# SAI — KHÔNG BAO GIỜ lấy tenant_id từ request
stmt = select(User).where(User.tenant_id == request.query_params["tenant_id"])
```

## JWT payload

```json
{
    "sub": 1,           // user_id
    "tid": 1,           // tenant_id  
    "role": "OWNER",    // OWNER | CASHIER
    "exp": 1716000000,  // expire (unix timestamp)
    "iat": 1715996400   // issued at
}
```

## Cấu hình .env

```
DATABASE_URL=postgresql+asyncpg://pos_user:pos_secret@localhost:5432/pos_db
JWT_SECRET_KEY=your-64-char-random-secret-key-change-in-production-xxx
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12
APP_ENV=development
```

## Quy tắc bảo mật

- Password: bcrypt cost=12, min 6 chars
- KHÔNG BAO GIỜ log password, trả password_hash trong response
- Login fail message luôn chung chung: "SĐT hoặc mật khẩu không đúng" (không tiết lộ SĐT có tồn tại)
- Rate limit login: 5 lần/5 phút/IP (dùng slowapi)
- Rate limit register: 3 lần/giờ/IP

## Thứ tự triển khai code

```
PHASE 1 — Project setup
  1. docker-compose.yml (PostgreSQL)
  2. .env.example + backend/config.py (pydantic Settings)
  3. backend/database.py (async engine, sessionmaker)  
  4. backend/shared/models.py (Base, AuditMixin)
  5. Alembic init + migration 001_initial (3 bảng: tenants, users, refresh_tokens)
  6. backend/main.py (FastAPI app skeleton)

PHASE 2 — Auth core
  7. backend/modules/tenant/models.py (Tenant model)
  8. backend/modules/auth/models.py (User, RefreshToken models)
  9. backend/modules/auth/utils.py (hash_password, verify_password, create_access_token, create_refresh_token, generate_slug)
  10. backend/modules/auth/schemas.py (RegisterRequest, LoginRequest, TokenResponse, etc.)
  11. backend/modules/auth/service.py (register, login, refresh, logout, change_password)
  12. backend/modules/auth/router.py (mount endpoints)
  13. backend/dependencies.py (get_db, get_current_user, require_role)
  14. backend/exceptions.py (custom error handler)

PHASE 3 — Staff management
  15. backend/modules/auth/schemas.py (thêm StaffCreate, StaffResponse, StaffList)
  16. backend/modules/auth/service.py (thêm create_staff, list_staff, deactivate_staff, activate_staff)
  17. backend/modules/auth/router.py (thêm /staff endpoints)

PHASE 4 — Tests
  18. tests/conftest.py (test DB, test client, fixtures)
  19. tests/test_auth.py (register, login, logout, change-password, refresh)
  20. tests/test_staff.py (create, list, deactivate, activate, permission checks)

PHASE 5 — Frontend (nếu cần)
  21. React project init (Vite + TS + Tailwind)
  22. API client + auth interceptor
  23. Auth store (Zustand)
  24. Login + Register pages
  25. Layout (Sidebar + Header + route guard)
  26. Staff management page
```

## Test cases cần pass

```
# Register
T01: Đăng ký thành công → 201, có tenant + user + tokens
T02: SĐT đã tồn tại → 409
T03: SĐT sai format → 422
T04: Password < 6 chars → 422
T05: Shop name rỗng → 422
T06: Slug trùng → 201 với slug có suffix

# Login
T07: Login thành công → 200, có tokens
T08: SĐT không tồn tại → 401 message chung
T09: Password sai → 401 message chung (giống T08)
T10: Tài khoản bị khóa → 403
T11: Tenant bị khóa → 403
T12: JWT payload đúng (decode verify sub, tid, role)

# Logout
T13: Logout thành công → 200, refresh token bị xóa khỏi DB
T14: Dùng refresh token cũ sau logout → 401

# Change password
T15: Đổi MK thành công → 200
T16: MK cũ sai → 400
T17: MK mới = MK cũ → 400
T18: Confirm không khớp → 422
T19: Sau đổi MK, refresh token cũ ở thiết bị khác → 401

# Staff (Owner only)
T20: Owner tạo NV → 201
T21: Cashier tạo NV → 403
T22: SĐT trùng trong tenant → 409
T23: NV mới login được → 200
T24: Owner khóa NV → 200, NV login → 403
T25: Owner tự khóa mình → 400
T26: Cashier khóa người khác → 403
T27: Mở khóa NV → 200, NV login lại được
```

## Ghi chú quan trọng

- Mọi bảng nghiệp vụ PHẢI có tenant_id
- ID dùng BIGSERIAL (không INT, không UUID)
- Tiền tệ dùng DECIMAL(15,2) — KHÔNG FLOAT
- Soft delete bằng deleted_at — không DELETE thật
- phone + email UNIQUE trong phạm vi 1 tenant (không phải toàn hệ thống)
- 1 SĐT có thể thuộc nhiều tenant (1 người sở hữu nhiều shop hoặc làm NV nhiều shop)
- Khi đăng ký: check SĐT toàn hệ thống (vì chưa có tenant)
- Khi mời NV: check SĐT trong tenant hiện tại
