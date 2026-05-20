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

## Database Schema — DDL đầy đủ (17 bảng)

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
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    phone           VARCHAR(20),
    email           VARCHAR(200),
    full_name       VARCHAR(200) NOT NULL,
    password_hash   VARCHAR(200) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'CASHIER',
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, phone),
    UNIQUE (tenant_id, email)
);

CREATE TABLE refresh_tokens (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(500) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Phần 2: Master Data — Sản phẩm, Khách hàng, NCC

```sql
CREATE TABLE categories (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    parent_id       BIGINT REFERENCES categories(id),
    name            VARCHAR(200) NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
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
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, sku),
    UNIQUE (tenant_id, barcode)
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
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, phone)
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
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT | COMPLETED | CANCELLED
    note            TEXT,
    completed_at    TIMESTAMPTZ,
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
    type            VARCHAR(20) NOT NULL,            -- SALE | RECEIPT | CANCEL_SALE | CANCEL_RECEIPT | ADJUSTMENT
    ref_type        VARCHAR(20) NOT NULL,            -- INVOICE | GOODS_RECEIPT
    ref_id          BIGINT NOT NULL,
    balance_after   DECIMAL(10,3) NOT NULL,          -- tồn sau giao dịch (debug)
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
```

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

        # 2. Validate tổng thanh toán >= tổng hóa đơn
        total_paid = sum(p.amount for p in payments)
        assert total_paid >= invoice.total

        # 3. Lock & kiểm tra tồn kho (SELECT FOR UPDATE tránh race condition)
        for item in invoice.items:
            inv = await db.execute(
                select(Inventory)
                .where(Inventory.tenant_id == tenant_id, Inventory.product_id == item.product_id)
                .with_for_update()
            )
            current_stock = inv.scalar_one_or_none().quantity or 0
            if current_stock < item.quantity and not product.allow_negative:
                raise "Không đủ tồn kho"

        # 4. Cập nhật trạng thái
        invoice.status = 'COMPLETED'
        invoice.completed_at = now()

        # 5. Snapshot giá vốn vào invoice_items
        for item in invoice.items:
            item.cost_price = product.cost_price
        invoice.cost_total = sum(item.quantity * item.cost_price)

        # 6. Tạo payments
        for p in payments:
            db.add(Payment(invoice_id=invoice.id, method=p.method, amount=p.amount))

        # 7. Trừ tồn kho: ghi kardex (stock_movements) + update cache (inventory)
        for item in invoice.items:
            new_balance = current_stock - item.quantity
            db.add(StockMovement(quantity=-item.quantity, type='SALE', ref_type='INVOICE', ref_id=invoice.id, balance_after=new_balance))
            inventory_row.quantity = new_balance

        # 8. Cập nhật thống kê KH nếu có
        if invoice.customer_id:
            customer.total_spent += invoice.total
            customer.total_orders += 1

    # 9. Ngoài transaction: trả response để FE in bill
```

### 2. Hoàn tất phiếu nhập kho

```python
async def complete_goods_receipt(db, tenant_id, receipt_id, user_id):
    async with db.begin():
        receipt = await get_receipt_with_items(db, tenant_id, receipt_id)
        receipt.status = 'COMPLETED'

        for item in receipt.items:
            # Tính giá vốn bình quân mới
            old_stock = inventory.quantity
            old_cost = product.cost_price
            new_cost = (old_stock * old_cost + item.quantity * item.cost_price) / (old_stock + item.quantity)
            product.cost_price = new_cost

            # Ghi kardex + cộng tồn
            new_balance = old_stock + item.quantity
            db.add(StockMovement(quantity=+item.quantity, type='RECEIPT', ...))
            inventory.quantity = new_balance
```

### 3. Hủy hóa đơn đã hoàn tất

```python
async def cancel_invoice(db, tenant_id, invoice_id, user_id, reason):
    # Tạo bút toán ngược — KHÔNG xóa dữ liệu cũ
    invoice.status = 'CANCELLED'
    for item in invoice.items:
        # Cộng lại tồn kho
        db.add(StockMovement(quantity=+item.quantity, type='CANCEL_SALE', ...))
        inventory.quantity += item.quantity
    # Trừ lại thống kê KH
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
| Hủy hóa đơn đã hoàn tất | ✅ | ❌ |
| Xem báo cáo lợi nhuận | ✅ | ❌ |
| Bán hàng (POS) | ✅ | ✅ |
| Tạo/sửa SP, KH | ✅ | ✅ |
| Nhập kho | ✅ | ✅ (GĐ 1 cho phép) |
| Xem doanh thu hôm nay | ✅ | ✅ |
