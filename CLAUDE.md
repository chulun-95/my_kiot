# CLAUDE.md — Hệ thống POS & Quản lý kho

## Dự án là gì

Hệ thống quản lý bán hàng và kho cho tạp hóa / siêu thị mini (giống KiotViet). Multi-tenant SaaS — mỗi shop là 1 tenant, dữ liệu hoàn toàn cách ly. Giai đoạn 1 (MVP) phục vụ 5-50 shop miễn phí.

## Tech stack

- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / Alembic / PostgreSQL 16
- **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS + Zustand
- **Auth:** JWT HS256 + bcrypt + refresh token rotation
- **Infra:** 1 VPS (Hetzner CX22), Nginx reverse proxy, Cloudflare CDN/SSL
- **Không dùng** Redis, message queue, microservices ở giai đoạn này

## Kiến trúc tổng quan

```
Browser (POS + Admin)
    │ HTTPS
    ▼
Cloudflare (SSL, CDN cho ảnh SP, DDoS protection)
    │
    ▼
VPS (1 máy duy nhất)
├── Nginx (reverse proxy + serve React build)
├── Uvicorn 4 workers (FastAPI app)
├── PostgreSQL 16 (multi-tenant, mọi bảng có tenant_id)
└── Cron (pg_dump backup đêm, cleanup expired tokens)
```

---

## 6 Module — 47 Use Cases

| Module | Prefix | Số UC | Mô tả |
|--------|--------|-------|-------|
| Auth & Tenant | UC-A | 8 | Đăng ký shop, đăng nhập, JWT, mời NV, phân quyền OWNER/CASHIER |
| Sản phẩm & Danh mục | UC-P | 8 | CRUD SP, nhóm hàng 2 cấp, barcode EAN-13, import Excel, SKU tự sinh |
| Khách hàng & NCC | UC-C | 6 | CRUD KH/NCC, tìm nhanh theo SĐT, lịch sử mua, thống kê chi tiêu |
| Bán hàng POS | UC-S | 10 | Quét barcode, giỏ hàng, thanh toán đa PT, in bill nhiệt, treo hóa đơn, hủy |
| Kho & Nhập hàng | UC-I | 7 | Phiếu nhập, tồn kho realtime, thẻ kho (kardex), giá vốn bình quân, cảnh báo |
| Báo cáo | UC-R | 6 | Dashboard, doanh thu, top SP, lợi nhuận, tồn kho |

### Thứ tự phát triển (phụ thuộc)

```
UC-A (Auth) ✅ DONE
  └──▸ UC-P (Sản phẩm) + UC-C (KH & NCC)     ← song song, không phụ thuộc nhau
          └──▸ UC-I (Kho & Nhập hàng)          ← cần Product + Supplier
          └──▸ UC-S (Bán hàng POS)             ← cần Product + Customer + Inventory
                  └──▸ UC-R (Báo cáo)          ← cần Invoice + Inventory data
```

---

## Cấu trúc project

```
pos-system/
├── CLAUDE.md
├── docker-compose.yml
├── .env / .env.example
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── backend/
│   ├── main.py                     # FastAPI app, mount routers, CORS, exception handlers
│   ├── config.py                   # pydantic Settings đọc từ .env
│   ├── database.py                 # async engine + async_sessionmaker
│   ├── dependencies.py             # get_db, get_current_user, require_role
│   ├── exceptions.py               # AppException + global error handler
│   ├── modules/
│   │   ├── auth/                   # ✅ DONE
│   │   │   ├── router.py           # /auth/register, /auth/login, /auth/logout, /auth/me, ...
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py           # User, RefreshToken
│   │   │   └── utils.py            # hash, verify, JWT, slug
│   │   ├── tenant/                 # ✅ DONE
│   │   │   ├── models.py           # Tenant
│   │   │   └── schemas.py
│   │   ├── product/
│   │   │   ├── router.py           # /products, /products/search, /products/barcode/{code}, /categories
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   └── models.py           # Product, Category, ProductImage
│   │   ├── customer/
│   │   │   ├── router.py           # /customers, /suppliers
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   └── models.py           # Customer, Supplier
│   │   ├── sales/
│   │   │   ├── router.py           # /invoices, /invoices/{id}/complete, /invoices/{id}/cancel
│   │   │   ├── service.py          # Luồng bán hàng (transaction, lock tồn kho, trừ stock)
│   │   │   ├── schemas.py
│   │   │   └── models.py           # Invoice, InvoiceItem, Payment
│   │   ├── inventory/
│   │   │   ├── router.py           # /goods-receipts, /inventory, /inventory/{pid}/movements
│   │   │   ├── service.py          # Nhập kho, giá vốn bình quân, kardex
│   │   │   ├── schemas.py
│   │   │   └── models.py           # GoodsReceipt, GoodsReceiptItem, StockMovement, Inventory
│   │   └── report/
│   │       ├── router.py           # /reports/dashboard, /reports/revenue, ...
│   │       ├── service.py          # SQL aggregate queries
│   │       └── schemas.py
│   └── shared/
│       ├── models.py               # Base, AuditMixin, TenantMixin
│       ├── pagination.py           # paginate(db, stmt, page, limit)
│       └── code_generator.py       # generate_code(db, tenant_id, prefix) → "HD20260517-001"
├── frontend/
│   ├── src/
│   │   ├── api/client.ts           # axios + interceptor auto refresh token
│   │   ├── stores/authStore.ts     # Zustand: user, tenant, tokens
│   │   ├── pages/
│   │   └── components/
└── tests/
```

---

## Database Schema — DDL đầy đủ (18 bảng)

### Nguyên tắc thiết kế (BẮT BUỘC tuân thủ)

1. **Mọi bảng nghiệp vụ có `tenant_id`** — filter theo tenant_id trong MỌI query
2. **PK dùng BIGSERIAL** — không INT, không UUID
3. **Tiền tệ dùng DECIMAL(15,2)** — KHÔNG BAO GIỜ dùng FLOAT
4. **Soft delete bằng `deleted_at`** — không DELETE thật
5. **Tồn kho = stock_movements (append-only kardex)**, bảng inventory chỉ là cache
6. **invoice_items snapshot** giá tại thời điểm bán — không phụ thuộc product hiện tại

### Phần 1: Foundation — Tenant & User (✅ DONE)

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

CREATE TABLE users (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES tenants(id),
    phone               VARCHAR(20),
    email               VARCHAR(200),
    full_name           VARCHAR(200) NOT NULL,
    password_hash       VARCHAR(200) NOT NULL,
    role                VARCHAR(20) NOT NULL DEFAULT 'CASHIER',
    is_active           BOOLEAN DEFAULT TRUE,
    failed_login_count  SMALLINT NOT NULL DEFAULT 0,        -- chống brute-force
    locked_until        TIMESTAMPTZ,                        -- khóa tạm khi vượt ngưỡng
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
    -- UNIQUE (tenant_id, phone) / (tenant_id, email) — xem Partial Unique Indexes ở Phần 7
);

CREATE TABLE refresh_tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(500) NOT NULL UNIQUE,
    family_id       UUID NOT NULL,                          -- cùng family = chuỗi rotation từ 1 lần đăng nhập
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,                            -- set khi rotate / logout / detect reuse
    replaced_by     VARCHAR(500),                           -- token mới sinh ra khi rotate
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Phần 1.5: `tenants.settings` JSONB — Canonical schema

Bảng `tenants.settings JSONB DEFAULT '{}'`. Mọi key dưới đây **đều optional** (có default ở app-layer), nhưng **đặt tên cố định** để tránh mỗi developer tự đặt khác nhau.

```jsonc
{
  // ---- POS / Bán hàng ----
  "allow_debt": false,                  // cho phép paid_amount < total khi complete invoice
  "default_payment_method": "CASH",     // payment mặc định khi mở POS
  "receipt_footer": "Cám ơn quý khách!", // text in cuối bill nhiệt

  // ---- Quyền hiển thị ----
  "show_cost_to_cashier": false,        // CASHIER có thấy cost_price ở list/search SP không
  "show_profit_to_cashier": false,      // (sẽ thêm khi có report)

  // ---- Kho ----
  "low_stock_threshold_default": 5,     // dùng nếu product.min_stock = 0
  "negative_stock_allowed_default": false, // override product.allow_negative

  // ---- Bill / mã ----
  "invoice_code_prefix": "HD",          // override 'HD' default
  "receipt_code_prefix": "NK",

  // ---- Phase 2 — chưa dùng ở MVP ----
  "tax_enabled": false,
  "tax_default_rate": 0.0
}
```

**Helper đọc settings ở backend:**
```python
def tenant_setting(tenant: Tenant, key: str, default):
    return (tenant.settings or {}).get(key, default)

# usage
if not tenant_setting(tenant, "allow_debt", False):
    raise AppError(...)
```

### Phần 2: Master Data — Sản phẩm, Khách hàng, NCC

```sql
CREATE TABLE categories (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    parent_id       BIGINT REFERENCES categories(id),
    name            VARCHAR(200) NOT NULL,
    depth           SMALLINT NOT NULL DEFAULT 1 CHECK (depth IN (1, 2)),  -- chỉ cho phép 2 cấp
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
    -- App-layer enforce: nếu parent_id != NULL thì parent.depth phải = 1 (con của con bị cấm)
);

CREATE TABLE products (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    category_id     BIGINT REFERENCES categories(id),
    sku             VARCHAR(50) NOT NULL,
    barcode         VARCHAR(50),
    name            VARCHAR(300) NOT NULL,
    description     TEXT,
    unit            VARCHAR(30) DEFAULT 'cái',
    cost_price      DECIMAL(15,2) NOT NULL DEFAULT 0,
    sale_price      DECIMAL(15,2) NOT NULL DEFAULT 0,
    min_stock       INTEGER DEFAULT 0,
    image_url       VARCHAR(500),
    status          VARCHAR(20) DEFAULT 'ACTIVE',   -- ACTIVE | INACTIVE | DRAFT
    allow_negative  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      BIGINT REFERENCES users(id),
    updated_by      BIGINT REFERENCES users(id),
    deleted_at      TIMESTAMPTZ
    -- UNIQUE (tenant_id, sku) / (tenant_id, barcode) — xem Partial Unique Indexes ở Phần 7
    -- (bắt buộc dùng partial vì phải cho phép tạo lại SKU/barcode sau khi soft-delete SP cũ)
);

CREATE TABLE product_images (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url       VARCHAR(500) NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE customers (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    phone           VARCHAR(20),
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    address         TEXT,
    note            TEXT,
    total_spent     DECIMAL(15,2) DEFAULT 0,
    total_orders    INTEGER DEFAULT 0,
    last_order_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
    -- UNIQUE (tenant_id, phone) — xem Partial Unique Indexes ở Phần 7
);

CREATE TABLE suppliers (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    name            VARCHAR(200) NOT NULL,
    phone           VARCHAR(20),
    email           VARCHAR(200),
    address         TEXT,
    tax_code        VARCHAR(20),
    note            TEXT,
    total_debt      DECIMAL(15,2) DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
```

### Phần 3: Transactions — Bán hàng

```sql
CREATE TABLE invoices (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    code            VARCHAR(30) NOT NULL,            -- HD20260517-001
    customer_id     BIGINT REFERENCES customers(id),
    cashier_id      BIGINT NOT NULL REFERENCES users(id),
    subtotal        DECIMAL(15,2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    total           DECIMAL(15,2) NOT NULL DEFAULT 0,
    cost_total      DECIMAL(15,2) NOT NULL DEFAULT 0,
    paid_amount     DECIMAL(15,2) NOT NULL DEFAULT 0,    -- tổng tiền KH đã trả (cho phép bán nợ: paid < total)
    change_amount   DECIMAL(15,2) NOT NULL DEFAULT 0,    -- tiền thối lại KH (nếu paid > total)
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT | COMPLETED | CANCELLED
    note            TEXT,
    completed_at    TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    cancelled_by    BIGINT REFERENCES users(id),
    cancel_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      BIGINT REFERENCES users(id),
    UNIQUE (tenant_id, code)
);

CREATE TABLE invoice_items (
    id              BIGSERIAL PRIMARY KEY,
    invoice_id      BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id      BIGINT NOT NULL REFERENCES products(id),
    product_name    VARCHAR(300) NOT NULL,           -- snapshot tại thời điểm bán
    product_sku     VARCHAR(50) NOT NULL,
    unit            VARCHAR(30),
    quantity        DECIMAL(10,3) NOT NULL,          -- DECIMAL vì tạp hóa bán cân (1.5 kg)
    unit_price      DECIMAL(15,2) NOT NULL,
    cost_price      DECIMAL(15,2) NOT NULL,          -- snapshot giá vốn tại thời điểm bán
    discount_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    line_total      DECIMAL(15,2) NOT NULL
);

CREATE TABLE payments (
    id              BIGSERIAL PRIMARY KEY,
    invoice_id      BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    method          VARCHAR(30) NOT NULL,            -- CASH | BANK_TRANSFER | MOMO | VNPAY
    amount          DECIMAL(15,2) NOT NULL,
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Phần 4: Transactions — Nhập kho

```sql
CREATE TABLE goods_receipts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    code            VARCHAR(30) NOT NULL,            -- NK20260517-001
    supplier_id     BIGINT REFERENCES suppliers(id),
    total           DECIMAL(15,2) NOT NULL DEFAULT 0,
    paid_amount     DECIMAL(15,2) NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    note            TEXT,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      BIGINT REFERENCES users(id),
    UNIQUE (tenant_id, code)
);

CREATE TABLE goods_receipt_items (
    id              BIGSERIAL PRIMARY KEY,
    receipt_id      BIGINT NOT NULL REFERENCES goods_receipts(id) ON DELETE CASCADE,
    product_id      BIGINT NOT NULL REFERENCES products(id),
    quantity        DECIMAL(10,3) NOT NULL,
    cost_price      DECIMAL(15,2) NOT NULL,
    line_total      DECIMAL(15,2) NOT NULL
);
```

### Phần 5: Inventory — Kho (trái tim hệ thống)

```sql
-- APPEND-ONLY: KHÔNG BAO GIỜ UPDATE hoặc DELETE dòng trong bảng này
CREATE TABLE stock_movements (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    product_id      BIGINT NOT NULL REFERENCES products(id),
    quantity        DECIMAL(10,3) NOT NULL,          -- dương = nhập, âm = xuất
    unit_cost       DECIMAL(15,2),                   -- snapshot giá vốn 1 đơn vị tại thời điểm move
    type            VARCHAR(20) NOT NULL,            -- SALE | RECEIPT | CANCEL_SALE | CANCEL_RECEIPT | ADJUSTMENT
    ref_type        VARCHAR(20) NOT NULL,            -- INVOICE | GOODS_RECEIPT | MANUAL
    ref_id          BIGINT NOT NULL,
    balance_after   DECIMAL(10,3) NOT NULL,          -- tồn sau giao dịch (debug + audit)
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      BIGINT NOT NULL REFERENCES users(id)
);

-- Cache tồn kho — derived từ SUM(stock_movements.quantity)
-- Có thể rebuild bất kỳ lúc nào
CREATE TABLE inventory (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    product_id      BIGINT NOT NULL REFERENCES products(id),
    quantity        DECIMAL(10,3) NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, product_id)
);
```

### Phần 6: System

```sql
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    action          VARCHAR(50) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       BIGINT,
    old_data        JSONB,
    new_data        JSONB,
    ip_address      VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE code_sequences (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    prefix          VARCHAR(10) NOT NULL,
    date_part       VARCHAR(8) NOT NULL,
    last_number     INTEGER NOT NULL DEFAULT 0,
    UNIQUE (tenant_id, prefix, date_part)
);
```

### Phần 7: Audit phụ trợ — Lịch sử giá

```sql
-- Tracking thay đổi cost_price / sale_price để báo cáo lợi nhuận chính xác theo thời gian
CREATE TABLE price_history (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    product_id      BIGINT NOT NULL REFERENCES products(id),
    field           VARCHAR(20) NOT NULL,            -- 'cost_price' | 'sale_price'
    old_value       DECIMAL(15,2),
    new_value       DECIMAL(15,2) NOT NULL,
    ref_type        VARCHAR(20) NOT NULL,            -- 'MANUAL' | 'GOODS_RECEIPT'
    ref_id          BIGINT,                          -- ID phiếu nhập nếu là RECEIPT
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by      BIGINT REFERENCES users(id)
);
```

### Phần 8: Indexes & Partial Unique Constraints (BẮT BUỘC)

Phần này tách riêng vì:
- **Partial unique** (`WHERE deleted_at IS NULL`) là yêu cầu chính khi đã soft-delete — UNIQUE inline trong CREATE TABLE sẽ chặn việc tái tạo SKU/phone/email sau khi xóa.
- Composite index theo `tenant_id` là **bắt buộc** cho mọi query nóng — không có thì 50 tenant × 10k row sẽ chậm thấy rõ ngay từ ngày 1.

```sql
-- === PARTIAL UNIQUE INDEXES (thay UNIQUE inline) ===
CREATE UNIQUE INDEX uq_users_tenant_phone
  ON users (tenant_id, phone) WHERE deleted_at IS NULL AND phone IS NOT NULL;
CREATE UNIQUE INDEX uq_users_tenant_email
  ON users (tenant_id, email) WHERE deleted_at IS NULL AND email IS NOT NULL;

CREATE UNIQUE INDEX uq_products_tenant_sku
  ON products (tenant_id, sku) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_products_tenant_barcode
  ON products (tenant_id, barcode) WHERE deleted_at IS NULL AND barcode IS NOT NULL;

CREATE UNIQUE INDEX uq_customers_tenant_phone
  ON customers (tenant_id, phone) WHERE deleted_at IS NULL AND phone IS NOT NULL;

-- === PERFORMANCE INDEXES ===
-- Products: danh sách / lọc trong admin
CREATE INDEX idx_products_tenant_active
  ON products (tenant_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_tenant_category
  ON products (tenant_id, category_id) WHERE deleted_at IS NULL;

-- Products: full-text search cho POS (gõ tên SP gợi ý)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_products_name_trgm
  ON products USING gin (name gin_trgm_ops) WHERE deleted_at IS NULL;

-- Inventory: lookup tồn theo SP
CREATE INDEX idx_inventory_tenant ON inventory (tenant_id, product_id);

-- Stock movements: kardex (thẻ kho) — CỰC quan trọng
CREATE INDEX idx_stock_movements_kardex
  ON stock_movements (tenant_id, product_id, created_at DESC);

-- Invoices: báo cáo doanh thu theo ngày
CREATE INDEX idx_invoices_tenant_completed
  ON invoices (tenant_id, completed_at DESC)
  WHERE status = 'COMPLETED';
-- Invoices: lịch sử mua của 1 KH
CREATE INDEX idx_invoices_customer
  ON invoices (tenant_id, customer_id, completed_at DESC)
  WHERE status = 'COMPLETED' AND customer_id IS NOT NULL;
-- Invoices: hóa đơn treo (drafts) theo cashier
CREATE INDEX idx_invoices_drafts
  ON invoices (tenant_id, cashier_id, created_at DESC)
  WHERE status = 'DRAFT';

-- Goods receipts: lịch sử nhập
CREATE INDEX idx_goods_receipts_tenant_completed
  ON goods_receipts (tenant_id, completed_at DESC)
  WHERE status = 'COMPLETED';

-- Customers / Suppliers: tìm theo tên (autocomplete)
CREATE INDEX idx_customers_name_trgm
  ON customers USING gin (name gin_trgm_ops) WHERE deleted_at IS NULL;

-- Refresh tokens: cleanup expired (cron đêm)
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens (expires_at);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens (family_id);

-- Audit logs: tra cứu theo entity
CREATE INDEX idx_audit_logs_entity
  ON audit_logs (tenant_id, entity_type, entity_id, created_at DESC);

-- Price history: tra cứu theo SP
CREATE INDEX idx_price_history_product
  ON price_history (tenant_id, product_id, changed_at DESC);
```

### Helper function — Sinh mã tự động

```sql
CREATE OR REPLACE FUNCTION generate_code(p_tenant_id BIGINT, p_prefix VARCHAR(10))
RETURNS VARCHAR(30) AS $$
DECLARE
    v_date_part VARCHAR(8);
    v_number INTEGER;
BEGIN
    v_date_part := TO_CHAR(NOW(), 'YYYYMMDD');
    INSERT INTO code_sequences (tenant_id, prefix, date_part, last_number)
    VALUES (p_tenant_id, p_prefix, v_date_part, 1)
    ON CONFLICT (tenant_id, prefix, date_part)
    DO UPDATE SET last_number = code_sequences.last_number + 1
    RETURNING last_number INTO v_number;
    RETURN p_prefix || v_date_part || '-' || LPAD(v_number::TEXT, 3, '0');
END;
$$ LANGUAGE plpgsql;
-- Ví dụ: SELECT generate_code(1, 'HD');  → 'HD20260517-001'
```

---

## API Endpoints — Tất cả module

### Auth & Tenant (✅ DONE)

```
POST   /api/v1/auth/register              Đăng ký shop mới
POST   /api/v1/auth/login                 Đăng nhập
POST   /api/v1/auth/refresh               Refresh token
POST   /api/v1/auth/logout                Đăng xuất
PUT    /api/v1/auth/change-password        Đổi mật khẩu
GET    /api/v1/auth/me                     Thông tin user hiện tại
GET    /api/v1/staff                       DS nhân viên (Owner)
POST   /api/v1/staff                       Mời NV (Owner)
PATCH  /api/v1/staff/{id}/deactivate       Khóa NV (Owner)
PATCH  /api/v1/staff/{id}/activate         Mở NV (Owner)
```

### Products & Categories

```
GET    /api/v1/products                    DS sản phẩm (phân trang, lọc, tìm)
GET    /api/v1/products/{id}               Chi tiết SP
POST   /api/v1/products                    Tạo SP mới
PUT    /api/v1/products/{id}               Sửa SP
DELETE /api/v1/products/{id}               Ngừng bán (soft delete)
GET    /api/v1/products/search?q=          Tìm nhanh cho POS (tên/SKU/barcode)
GET    /api/v1/products/barcode/{code}     Tìm chính xác theo barcode
POST   /api/v1/products/import             Import từ Excel

GET    /api/v1/categories                  DS nhóm hàng (dạng cây)
POST   /api/v1/categories                  Tạo nhóm
PUT    /api/v1/categories/{id}             Sửa nhóm
DELETE /api/v1/categories/{id}             Xóa nhóm (chặn nếu có SP)
```

### Customers & Suppliers

```
GET    /api/v1/customers                   DS khách hàng
GET    /api/v1/customers/{id}              Chi tiết + lịch sử mua
POST   /api/v1/customers                   Tạo KH
PUT    /api/v1/customers/{id}              Sửa KH
GET    /api/v1/customers/phone/{phone}     Tìm nhanh theo SĐT (POS)

GET    /api/v1/suppliers                   DS nhà cung cấp
POST   /api/v1/suppliers                   Tạo NCC
PUT    /api/v1/suppliers/{id}              Sửa NCC
```

### Sales / POS (Bán hàng)

```
POST   /api/v1/invoices                    Tạo hóa đơn nháp
GET    /api/v1/invoices/{id}               Chi tiết hóa đơn
PUT    /api/v1/invoices/{id}               Sửa hóa đơn nháp (thêm/bớt SP)
POST   /api/v1/invoices/{id}/complete      Hoàn tất + thanh toán
POST   /api/v1/invoices/{id}/cancel        Hủy hóa đơn (Owner only)
GET    /api/v1/invoices                    Lịch sử hóa đơn
GET    /api/v1/invoices/drafts             DS hóa đơn treo
```

### Inventory / Goods Receipts (Kho & Nhập hàng)

```
POST   /api/v1/goods-receipts                  Tạo phiếu nhập nháp
GET    /api/v1/goods-receipts/{id}             Chi tiết
PUT    /api/v1/goods-receipts/{id}             Sửa nháp
POST   /api/v1/goods-receipts/{id}/complete    Hoàn tất (cộng tồn + tính giá vốn)
POST   /api/v1/goods-receipts/{id}/cancel      Hủy
GET    /api/v1/goods-receipts                  Lịch sử nhập

GET    /api/v1/inventory                       Tồn kho hiện tại
GET    /api/v1/inventory/{product_id}/movements Thẻ kho (kardex)
GET    /api/v1/inventory/low-stock             Hàng sắp hết

POST   /api/v1/inventory/adjustments           Điều chỉnh tồn (kiểm kê, hỏng, mất) — OWNER only
GET    /api/v1/inventory/adjustments           Lịch sử điều chỉnh
```

**Body `POST /inventory/adjustments`:**
```json
{
  "items": [
    {"product_id": 1, "new_quantity": 42.5, "reason": "Kiểm kê tháng"},
    {"product_id": 7, "new_quantity": 0,    "reason": "Hỏng do ẩm"}
  ]
}
```

Logic: với mỗi item → LOCK inventory → tính `delta = new_quantity - old_quantity` → ghi 1 row `stock_movements` với `type='ADJUSTMENT'`, `ref_type='MANUAL'`, `ref_id=user_id`, `note=reason` → update inventory cache. Cho phép âm nếu `product.allow_negative=true`.

### Reports (Báo cáo)

```
GET    /api/v1/reports/dashboard               Tổng quan hôm nay
GET    /api/v1/reports/revenue?from=&to=&group_by=  Doanh thu
GET    /api/v1/reports/top-products             Top SP bán chạy
GET    /api/v1/reports/profit                   Lợi nhuận
GET    /api/v1/reports/stock-summary            Tổng quan tồn kho
```

---

## Business Logic quan trọng

### 1. Hoàn tất hóa đơn (use case quan trọng nhất)

```python
async def complete_invoice(db, tenant_id, invoice_id, payments, cashier_id):
    async with db.begin():
        # 1. Lấy hóa đơn DRAFT + items
        invoice = await get_invoice_with_items(db, tenant_id, invoice_id)
        assert invoice.status == 'DRAFT'

        # 2. Validate tiền: paid >= total (hoặc cho phép bán nợ tùy setting)
        total_paid = sum(p.amount for p in payments)
        if total_paid < invoice.total and not tenant_settings.allow_debt:
            raise AppException('INSUFFICIENT_PAYMENT')

        # 3. Lock tồn kho — LOCK THEO product_id ASC để tránh deadlock
        #    (2 hóa đơn cùng SP A+B nhưng đảo thứ tự cart sẽ deadlock nếu không sort)
        product_ids = sorted({item.product_id for item in invoice.items})

        # 3a. BẮT BUỘC: Upsert inventory row trước khi lock (PostgreSQL-level, không phải Python-level)
        #     Vấn đề: 2 POS cùng bán SP allow_negative chưa có inventory row →
        #       cả 2 SELECT FOR UPDATE thấy rỗng → cả 2 INSERT → Unique Violation
        #     Fix: INSERT ON CONFLICT DO NOTHING (atomic ở DB) → đảm bảo row tồn tại trước khi lock
        #     Chỉ cần thiết cho SP allow_negative=True, nhưng apply cho tất cả để code đơn giản hơn.
        for pid in product_ids:
            await db.execute(
                insert(Inventory)
                .values(tenant_id=tenant_id, product_id=pid, quantity=0)
                .on_conflict_do_nothing(index_elements=["tenant_id", "product_id"])
            )
        await db.flush()

        inv_rows = (await db.execute(
            select(Inventory)
            .where(Inventory.tenant_id == tenant_id, Inventory.product_id.in_(product_ids))
            .order_by(Inventory.product_id)
            .with_for_update()
        )).scalars().all()
        inv_by_pid = {r.product_id: r for r in inv_rows}

        # 4. Kiểm tra đủ tồn (gom toàn bộ thiếu để báo 1 lần, UX tốt hơn)
        shortages = []
        for item in invoice.items:
            current = inv_by_pid[item.product_id].quantity if item.product_id in inv_by_pid else 0
            if current < item.quantity and not item.product.allow_negative:
                shortages.append({'product_id': item.product_id, 'need': item.quantity, 'have': current})
        if shortages:
            raise AppException('INSUFFICIENT_STOCK', details=shortages)

        # 5. Cập nhật trạng thái + snapshot giá vốn TẠI THỜI ĐIỂM COMPLETE
        invoice.status = 'COMPLETED'
        invoice.completed_at = now()
        invoice.paid_amount = total_paid
        invoice.change_amount = max(0, total_paid - invoice.total)
        for item in invoice.items:
            item.cost_price = item.product.cost_price   # snapshot ngay tại đây
        invoice.cost_total = sum(item.quantity * item.cost_price for item in invoice.items)

        # 6. Tạo payments
        for p in payments:
            db.add(Payment(invoice_id=invoice.id, method=p.method, amount=p.amount))

        # 7. Trừ tồn: ghi kardex (append-only) + update cache (inventory)
        for item in invoice.items:
            inv = inv_by_pid[item.product_id]
            new_balance = inv.quantity - item.quantity
            db.add(StockMovement(
                tenant_id=tenant_id, product_id=item.product_id,
                quantity=-item.quantity, unit_cost=item.cost_price,
                type='SALE', ref_type='INVOICE', ref_id=invoice.id,
                balance_after=new_balance, created_by=cashier_id,
            ))
            inv.quantity = new_balance

        # 8. Cập nhật thống kê KH nếu có
        if invoice.customer_id:
            customer.total_spent += invoice.total
            customer.total_orders += 1
            customer.last_order_at = now()

    # 9. Ngoài transaction: trả response để FE in bill
```

### 2. Hoàn tất phiếu nhập kho

```python
async def complete_goods_receipt(db, tenant_id, receipt_id, user_id):
    async with db.begin():
        receipt = await get_receipt_with_items(db, tenant_id, receipt_id)
        assert receipt.status == 'DRAFT'

        # 1. LOCK inventory rows theo product_id ASC (cùng quy ước với complete_invoice)
        product_ids = sorted({item.product_id for item in receipt.items})
        inv_rows = (await db.execute(
            select(Inventory)
            .where(Inventory.tenant_id == tenant_id, Inventory.product_id.in_(product_ids))
            .order_by(Inventory.product_id)
            .with_for_update()
        )).scalars().all()
        inv_by_pid = {r.product_id: r for r in inv_rows}
        # Tạo row inventory nếu SP chưa có
        for pid in product_ids:
            if pid not in inv_by_pid:
                row = Inventory(tenant_id=tenant_id, product_id=pid, quantity=0)
                db.add(row); inv_by_pid[pid] = row

        receipt.status = 'COMPLETED'
        receipt.completed_at = now()

        for item in receipt.items:
            inv = inv_by_pid[item.product_id]
            product = await get_product_for_update(db, tenant_id, item.product_id)

            old_stock = inv.quantity
            old_cost = product.cost_price

            # Giá vốn bình quân — chỉ tính khi old_stock > 0
            # BẮT BUỘC: nếu old_stock <= 0 (âm do allow_negative hoặc = 0), dùng giá nhập mới
            # Lý do: old_stock âm trong công thức tạo ra new_cost lớn hơn giá nhập thực → sai lệch lợi nhuận
            # Ví dụ: old_stock=-2, old_cost=10, qty=5, in_cost=20 → (−20+100)/3 = 26.67 (sai) vs 20.00 (đúng)
            if old_stock <= 0:
                new_cost = item.cost_price
            else:
                new_cost = (old_stock * old_cost + item.quantity * item.cost_price) / (old_stock + item.quantity)

            # Ghi lịch sử giá nếu cost thay đổi
            if new_cost != old_cost:
                db.add(PriceHistory(
                    tenant_id=tenant_id, product_id=product.id,
                    field='cost_price', old_value=old_cost, new_value=new_cost,
                    ref_type='GOODS_RECEIPT', ref_id=receipt.id, changed_by=user_id,
                ))
                product.cost_price = new_cost

            # Ghi kardex + cộng tồn
            new_balance = old_stock + item.quantity
            db.add(StockMovement(
                tenant_id=tenant_id, product_id=product.id,
                quantity=+item.quantity, unit_cost=item.cost_price,
                type='RECEIPT', ref_type='GOODS_RECEIPT', ref_id=receipt.id,
                balance_after=new_balance, created_by=user_id,
            ))
            inv.quantity = new_balance
```

### 3. Hủy hóa đơn đã hoàn tất

```python
async def cancel_invoice(db, tenant_id, invoice_id, user_id, reason):
    async with db.begin():
        invoice = await get_invoice_with_items(db, tenant_id, invoice_id)
        assert invoice.status == 'COMPLETED'   # chỉ cancel hóa đơn đã hoàn tất

        # 1. LOCK inventory theo product_id ASC (cùng quy ước)
        product_ids = sorted({item.product_id for item in invoice.items})
        inv_rows = (await db.execute(
            select(Inventory)
            .where(Inventory.tenant_id == tenant_id, Inventory.product_id.in_(product_ids))
            .order_by(Inventory.product_id)
            .with_for_update()
        )).scalars().all()
        inv_by_pid = {r.product_id: r for r in inv_rows}

        # 2. Bút toán ngược — KHÔNG xóa dữ liệu cũ, KHÔNG đụng invoice_items
        invoice.status = 'CANCELLED'
        invoice.cancelled_at = now()
        invoice.cancelled_by = user_id
        invoice.cancel_reason = reason

        for item in invoice.items:
            inv = inv_by_pid[item.product_id]
            new_balance = inv.quantity + item.quantity
            db.add(StockMovement(
                tenant_id=tenant_id, product_id=item.product_id,
                quantity=+item.quantity, unit_cost=item.cost_price,
                type='CANCEL_SALE', ref_type='INVOICE', ref_id=invoice.id,
                balance_after=new_balance, created_by=user_id,
                note=f'Hủy hóa đơn: {reason}',
            ))
            inv.quantity = new_balance

        # 3. Trừ lại thống kê KH (nếu có)
        if invoice.customer_id:
            customer.total_spent -= invoice.total
            customer.total_orders -= 1
```

### 4. Sinh mã tự động

Hóa đơn: HD20260517-001, HD20260517-002...
Phiếu nhập: NK20260517-001...
SKU sản phẩm: SP000001, SP000002... (nếu không nhập tay)
Dùng bảng `code_sequences` + function `generate_code()` với advisory lock.

### 5. Xử lý race condition bán hàng

2 thu ngân cùng bán 1 SP còn 1 cái → dùng `SELECT FOR UPDATE` lock dòng inventory. Thu ngân B phải chờ A commit xong, khi đọc thấy tồn = 0 → từ chối.

---

## Shared patterns (BẮT BUỘC)

### Tenant isolation — QUY TẮC VÀNG

```python
# ĐÚNG — tenant_id từ JWT
stmt = select(Product).where(Product.tenant_id == current_user.tenant_id)

# SAI — KHÔNG BAO GIỜ từ request
stmt = select(Product).where(Product.tenant_id == request.query_params["tenant_id"])
```

### Response format chuẩn

```json
// List
{"items": [...], "pagination": {"page": 1, "limit": 20, "total": 156, "total_pages": 8}}

// Single
{"id": 1, "name": "...", ...}

// Error
{"error": {"code": "INSUFFICIENT_STOCK", "message": "SP X chỉ còn 5, yêu cầu 10", "details": {...}}}
```

### HTTP status codes

200 (GET/PUT/PATCH OK), 201 (POST created), 400 (business rule fail), 401 (unauthenticated), 403 (forbidden), 404 (not found), 409 (conflict/duplicate), 422 (validation), 500 (server error)

### Pagination helper

```python
async def paginate(db, stmt, page=1, limit=20):
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
    items = (await db.execute(stmt.offset((page-1)*limit).limit(limit))).scalars().all()
    return {"items": items, "pagination": {"page": page, "limit": limit, "total": total, "total_pages": ceil(total/limit)}}
```

---

## Cấu hình .env

```
DATABASE_URL=postgresql+asyncpg://pos_user:pos_secret@localhost:5432/pos_db
JWT_SECRET_KEY=<64-char-random>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12
APP_ENV=development
```

---

## Đặc thù tạp hóa / siêu thị mini

- **Đơn vị tính linh hoạt:** cái, gói, chai, lon, kg, lạng, lít, thùng, lốc, hộp, túi, bịch, cuộn...
- **Bán cân:** quantity dùng DECIMAL(10,3) — hỗ trợ 1.5 kg, 0.3 kg
- **Giá bán linh hoạt:** cho phép override giá trên từng dòng hóa đơn (không bắt buộc theo sale_price)
- **Barcode:** hàng tạp hóa có sẵn EAN-13 trên bao bì, máy quét USB hoạt động như keyboard
- **Khách vãng lai:** customer_id = null trên invoice, không bắt buộc chọn KH
- **Thanh toán đa phương thức:** 1 hóa đơn có thể thanh toán bằng nhiều cách (tiền mặt + chuyển khoản)

---

## Phân quyền (2 role)

| Chức năng | OWNER | CASHIER |
|-----------|-------|---------|
| Quản lý NV (mời, khóa) | ✅ | ❌ |
| **Hủy hóa đơn DRAFT** (treo bỏ) | ✅ | ✅ (chỉ của chính mình) |
| **Hủy hóa đơn COMPLETED** (đã hoàn tất) | ✅ | ❌ |
| **Hủy phiếu nhập DRAFT** | ✅ | ✅ |
| **Hủy phiếu nhập COMPLETED** | ✅ | ❌ |
| **Điều chỉnh tồn kho** (stocktake/adjustment) | ✅ | ❌ |
| Xem báo cáo lợi nhuận | ✅ | ❌ |
| Xem giá vốn sản phẩm | ✅ | ⚠️ (theo `tenant.settings.show_cost_to_cashier`) |
| Bán hàng (POS) | ✅ | ✅ |
| Tạo/sửa SP, KH, NCC | ✅ | ✅ |
| Xóa SP/KH/NCC (soft) | ✅ | ❌ |
| Tạo nhóm hàng | ✅ | ✅ |
| Xóa nhóm hàng | ✅ | ❌ |
| Nhập kho (tạo/sửa DRAFT, complete) | ✅ | ✅ (GĐ 1 cho phép) |
| Xem doanh thu hôm nay | ✅ | ✅ |

---

## Audit logging — Quy ước (BẮT BUỘC)

Bảng `audit_logs` đã có trong DDL Phần 6. Quy tắc khi nào ghi và format:

### Khi nào ghi

| Hành động | Có ghi audit? |
|-----------|---------------|
| CREATE entity (POST) | ✅ — `new_data` = snapshot sau khi tạo |
| UPDATE entity (PUT/PATCH) | ✅ — `old_data` + `new_data` (chỉ diff các field thay đổi) |
| DELETE / soft-delete | ✅ — `old_data` = snapshot trước xóa |
| Business actions: complete invoice, cancel invoice, complete receipt, cancel receipt, stock adjustment | ✅ — `new_data` chứa key chính (ví dụ `{"invoice_id": 1, "total": 150000}`) |
| READ (GET) | ❌ — không ghi |
| Login/logout | ❌ — đã có `last_login_at` + log từ slowapi |

### Action enum chuẩn

```
CREATE_PRODUCT      UPDATE_PRODUCT      DELETE_PRODUCT
CREATE_CATEGORY     UPDATE_CATEGORY     DELETE_CATEGORY
CREATE_CUSTOMER     UPDATE_CUSTOMER     DELETE_CUSTOMER
CREATE_SUPPLIER     UPDATE_SUPPLIER     DELETE_SUPPLIER
CREATE_INVOICE      UPDATE_INVOICE      COMPLETE_INVOICE     CANCEL_INVOICE
CREATE_RECEIPT      UPDATE_RECEIPT      COMPLETE_RECEIPT     CANCEL_RECEIPT
STOCK_ADJUSTMENT
CREATE_STAFF        UPDATE_STAFF        DEACTIVATE_STAFF     ACTIVATE_STAFF
```

### Helper (thêm vào `backend/shared/audit.py`)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from backend.modules.system.models import AuditLog  # bảng audit_logs

async def write_audit(
    db: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(AuditLog(
        tenant_id=tenant_id, user_id=user_id, action=action,
        entity_type=entity_type, entity_id=entity_id,
        old_data=old_data, new_data=new_data, ip_address=ip_address,
    ))
    # KHÔNG commit ở đây — caller quyết định trong cùng transaction
```

### Quy tắc về `old_data` / `new_data`

- Chỉ chứa **scalar fields** (id, name, prices, status, ...) — KHÔNG dump cả relationship
- Cho UPDATE: chỉ ghi field **thực sự thay đổi** (diff), giúp đọc log dễ
- Cho CREATE: ghi toàn bộ field công khai (không hash password, không token)

---

## Price history — Quy tắc ghi

Bảng `price_history` ghi MỌI thay đổi `cost_price` / `sale_price` của product:

| Tình huống | `field` | `ref_type` | `ref_id` |
|-----------|---------|-----------|----------|
| Owner sửa giá qua `PUT /products/{id}` | `cost_price` hoặc `sale_price` | `MANUAL` | `user_id` |
| Complete goods_receipt → cost thay đổi do bình quân | `cost_price` | `GOODS_RECEIPT` | `receipt_id` |
| Import Excel có cột giá → giá thay đổi | `cost_price` / `sale_price` | `IMPORT` | `import_batch_id` (nếu có) |
| Stocktake adjustment | **KHÔNG ghi** (chỉ thay đổi quantity, không thay đổi giá) | — | — |

**Lưu ý:** chỉ ghi khi giá **thực sự khác** giá cũ. Không ghi nếu `old_value == new_value`.

---

## Security & Operations

### Brute-force protection cho /auth/login

- Mỗi lần sai mật khẩu → `failed_login_count += 1`
- Khi `failed_login_count >= 5` → set `locked_until = NOW() + 15 minutes`, trả 429
- Login thành công → reset về 0 và xóa `locked_until`
- Vì không có Redis, dùng cột trên bảng `users` (đã thêm trong DDL Phần 1)
- Thêm `slowapi` middleware cho IP-based rate limit ở tầng app: 10 req/phút/IP cho `/auth/login`, `/auth/register`

### Refresh token rotation (chống reuse attack)

```python
async def rotate_refresh_token(db, old_token_str):
    old = await db.scalar(select(RefreshToken).where(RefreshToken.token == old_token_str))
    if old is None or old.expires_at < now():
        raise AppException('INVALID_REFRESH_TOKEN')

    # REUSE DETECTION: token đã revoke nhưng vẫn được dùng → bị đánh cắp
    if old.revoked_at is not None:
        # Revoke toàn bộ family — buộc user login lại từ đầu
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == old.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now())
        )
        raise AppException('REFRESH_TOKEN_REUSE_DETECTED')

    new_token = generate_refresh_token()
    db.add(RefreshToken(
        user_id=old.user_id, token=new_token,
        family_id=old.family_id,                        # giữ nguyên family
        expires_at=now() + timedelta(days=30),
    ))
    old.revoked_at = now()
    old.replaced_by = new_token
    return new_token
```

### Lưu token ở frontend

- **Access token (1h):** giữ trong memory (Zustand store, KHÔNG vào localStorage) → tránh XSS đọc được
- **Refresh token (30d):** HttpOnly + Secure + SameSite=Strict cookie → JS không đọc được
- CSRF protection: backend kiểm header `X-Requested-With: XMLHttpRequest` cho mọi state-changing request (axios mặc định gửi)

### File upload — ảnh sản phẩm

- **Lưu trữ:** Cloudflare R2 bucket (S3-compatible, 10GB miễn phí). Đã có Cloudflare làm CDN → tận dụng tiếp.
- **Convention:** key = `tenants/{tenant_id}/products/{product_id}/{uuid}.webp`
- **Pipeline upload:** FE upload trực tiếp lên R2 qua presigned URL backend cấp (không proxy qua VPS, tiết kiệm băng thông).
- **Resize:** Cloudflare Images hoặc tự convert sang webp 800px max trước khi lưu (Pillow ở backend).
- **`image_url` trong DB:** lưu key R2 (relative), FE ghép với domain CDN khi render.

### Backup & retention

- **pg_dump hằng đêm** → tải về máy nhà mỗi tuần (cron + rclone lên Google Drive).
- **audit_logs / stock_movements / price_history:** retention 1 năm. Cron tháng: xóa rows > 365 ngày (hoặc move sang bảng `*_archive`).
- **refresh_tokens:** cron mỗi giờ xóa rows có `expires_at < NOW() - 7 days`.

### Timezone

- DB lưu `TIMESTAMPTZ` (UTC).
- API trả ISO 8601 có offset, FE convert sang `Asia/Ho_Chi_Minh` để hiển thị.
- Báo cáo "doanh thu ngày" → `WHERE completed_at AT TIME ZONE 'Asia/Ho_Chi_Minh' BETWEEN ...`.

---

## Scope phase 1 — Quyết định "không làm"

Ghi rõ ở đây để khỏi vô tình build dở rồi vứt:

| Tính năng | Trạng thái | Lý do |
|-----------|-----------|-------|
| **Multi-warehouse** (nhiều kho/shop) | ❌ Phase 2 | Hiện `inventory.UNIQUE (tenant_id, product_id)` ngầm định 1 kho. Khi support, đổi thành `(tenant_id, warehouse_id, product_id)` và thêm bảng `warehouses`. |
| **Product variants** (size/màu) | ❌ Phase 2 | Tạp hóa chủ yếu bán SKU đơn. Nếu cần → thêm `product_variants` (parent_product_id, attributes JSONB). |
| **Khuyến mãi/voucher engine** | ❌ Phase 2 | MVP chỉ cho `discount_amount` thủ công trên từng dòng / cả hóa đơn. |
| **Hóa đơn VAT (xuất hóa đơn đỏ)** | ❌ Phase 2 | Tạp hóa MVP không cần. Khi thêm: cột `tax_code`, `tax_rate`, `tax_amount` trên invoices + items. |
| **Bán nợ phức tạp** (sổ công nợ) | ⚠️ Đơn giản | DDL có `paid_amount` để bán nợ 1 lần, nhưng KHÔNG có module sổ công nợ riêng. |
| **Báo cáo FIFO / LIFO cost** | ❌ Phase 2 | Chỉ làm giá vốn bình quân (moving average). |
| **Đa NCC/SP** (`product_suppliers`) | ❌ Phase 2 | Phiếu nhập đủ để biết đã mua từ NCC nào. Khi cần báo cáo "SP X mua bao nhiêu NCC" → thêm bảng nối. |
| **Realtime (WebSocket) đồng bộ POS** | ❌ Phase 2 | 1 ca chỉ 1-2 thu ngân, refresh thủ công đủ dùng. |
| **Mobile app / PWA offline** | ❌ Phase 2 | Web responsive đủ cho MVP. |

---

## Migration checklist khi vào module mới

Trước khi bắt đầu code 1 module (UC-P, UC-C, UC-I, UC-S, UC-R), kiểm:

1. ✅ Đã tạo Alembic migration cho các bảng + indexes của module đó chưa?
2. ✅ Đã verify partial unique index hoạt động (test soft-delete rồi tạo lại cùng key)?
3. ✅ Mọi query trong service.py đã filter `tenant_id` chưa? (grep `select(` để check)
4. ✅ Mọi mutation có ghi audit_logs (action + entity + old/new) chưa? (xem Audit logging section)
5. ✅ Endpoint mutation có require_role đúng chưa?
6. ✅ Test integration: ít nhất 1 test "tenant A không thấy data tenant B"
7. ✅ Khi sửa giá SP / cost từ goods_receipt → có ghi `price_history` chưa?

---

## Backlog — Issues chưa fix (sẽ xử lý sau khi xong MVP)

Đã có giải pháp nhưng defer để không phình scope phase 1. Mỗi item ghi rõ workaround hiện tại.

| # | Vấn đề | Workaround MVP | Khi nào fix |
|---|--------|-----------------|--------------|
| 🟡 1 | `generate_code` SQL function vs Python | Dùng Python `backend/shared/code_generator.py` với `with_for_update()` lock. SQL function trong spec chỉ là tham khảo. | Khi cần đẩy logic xuống DB để giảm round-trip |
| 🟡 2 | `product_images` bảng có nhưng chưa có API | Phase 1 chỉ dùng `products.image_url` (1 ảnh chính). Bảng `product_images` defer. | Phase 2 khi cần gallery nhiều ảnh |
| 🟡 3 | `POST /products/import` (Excel) | Chưa implement. UX hiện tại: owner tạo từng SP. | Khi onboarding shop > 100 SP |
| 🟢 4 | Cost visibility cho CASHIER | Field `tenant.settings.show_cost_to_cashier`. Response service kiểm tra và set `cost_price = None` nếu false. | Implement khi build Phase 4 (POS) |
| 🟢 5 | Cashier shift / pos_session | Không có. 1 ca = 1 working day, đối chiếu tay. | Phase 2 — thêm bảng `pos_sessions` |
| 🟢 6 | Phone format chỉ VN | Regex `^0[3|5|7|8|9]\d{8}$`. International defer. | Phase 2 — chuyển E.164 |
| 🟢 7 | Idempotency cho `complete_invoice` | Không có. Nếu client retry → có thể double-spend. UX hiện tại: FE disable nút sau click. | Phase 1.5 — thêm header `Idempotency-Key` + bảng `idempotency_keys` |
| 🟢 8 | Soft-delete customer/supplier có lịch sử | Cho phép xóa. Invoice/Receipt cũ vẫn ref `customer_id` → khi join thấy NULL. Display "Khách đã xóa". | Phase 2 — thêm `invoices.customer_name_snapshot` |
| 🟡 9 | Đơn vị quy đổi (thùng/lốc → lon) | Phase 1: nhập/bán theo đơn vị cơ bản (lon/chai). | Phase 2 — thêm bảng `product_units (product_id, unit_name, conversion_rate, sale_price, barcode)`. 1 SP nhiều đơn vị tính, tồn kho chỉ theo đơn vị cơ bản. Pattern: KiotViet/Sapo. |
