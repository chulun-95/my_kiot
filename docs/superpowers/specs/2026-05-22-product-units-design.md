# Product Units — Đơn vị quy đổi (thùng/lốc → lon)

**Date:** 2026-05-22
**Status:** Approved
**Phase:** 1 (MVP)

## Mục tiêu

Cho phép kho quản lý hàng hóa theo đơn vị lớn hơn (thùng, lốc, hộp) thay vì phải nhập từng đơn vị cơ bản (lon, chai, cái). Cashier có thể bán và nhập kho theo thùng; hệ thống tự quy đổi về đơn vị cơ bản để tính tồn kho.

**Flows áp dụng:** Goods Receipt (nhập kho), POS Invoice (bán hàng), Inventory Display (xem tồn).

---

## Schema

### Bảng mới: `product_units`

```sql
CREATE TABLE product_units (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    unit_name       VARCHAR(30) NOT NULL,           -- 'thùng', 'lốc', 'hộp'
    conversion_rate DECIMAL(10,3) NOT NULL           -- 1 đơn vị này = N đơn vị cơ bản (phải > 1)
                    CHECK (conversion_rate > 1),
    sale_price      DECIMAL(15,2),                  -- giá bán riêng (null = product.sale_price × conversion_rate)
    barcode         VARCHAR(50),                    -- barcode riêng của đơn vị này
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, product_id, unit_name)
);

CREATE UNIQUE INDEX uq_product_units_tenant_barcode
  ON product_units (tenant_id, barcode) WHERE barcode IS NOT NULL;

CREATE INDEX idx_product_units_product
  ON product_units (tenant_id, product_id);
```

**Quy ước:** `products.unit` là đơn vị cơ bản (lon, chai, cái...). Inventory luôn tính theo đơn vị cơ bản. `product_units` chỉ chứa đơn vị QUY ĐỔI (không bao gồm base unit).

### Thay đổi `goods_receipt_items`

Thêm 3 cột:
```sql
unit_id         BIGINT REFERENCES product_units(id) ON DELETE SET NULL,
unit_name       VARCHAR(30),          -- snapshot tại thời điểm tạo (null = base unit)
conversion_rate DECIMAL(10,3)         -- snapshot (null hoặc 1 = base unit)
```

### Thay đổi `invoice_items`

Thêm 2 cột (đã có sẵn cột `unit`):
```sql
unit_id         BIGINT REFERENCES product_units(id) ON DELETE SET NULL,
conversion_rate DECIMAL(10,3)         -- snapshot (null hoặc 1 = base unit)
```

Khi `unit_id` là null: transaction dùng đơn vị cơ bản (backward compatible với dữ liệu cũ).

---

## Business Logic

### complete_goods_receipt — Quy đổi khi nhập kho

```python
for item in receipt.items:
    rate = Decimal(item.conversion_rate or 1)
    base_qty = item.quantity * rate           # 2 thùng × 24 = 48 lon
    cost_per_base = item.cost_price / rate    # 240,000 ÷ 24 = 10,000/lon

    # Giá vốn bình quân (dùng base_qty và cost_per_base)
    old_stock = inv.quantity
    if old_stock <= 0:
        new_cost = cost_per_base              # rule: khi tồn <= 0, không dùng bình quân
    else:
        new_cost = (old_stock * old_cost + base_qty * cost_per_base) / (old_stock + base_qty)

    inv.quantity += base_qty                  # +48 lon
    # StockMovement: quantity=+base_qty, unit_cost=cost_per_base
```

### complete_invoice — Quy đổi khi bán hàng

```python
for item in invoice.items:
    rate = Decimal(item.conversion_rate or 1)
    base_qty = item.quantity * rate           # 1 thùng × 24 = 24 lon

    # cost_price snapshot theo đơn vị cơ bản (lon)
    item.cost_price = product.cost_price      # 10,000/lon
    cost_total += item.cost_price * base_qty  # 10,000 × 24 = 240,000

    # Trừ tồn
    inv.quantity -= base_qty                  # -24 lon
    # StockMovement: quantity=-base_qty, unit_cost=item.cost_price
```

**Invoice item lưu:** `quantity=1, unit="thùng", conversion_rate=24, unit_price=240,000` → `line_total = 1 × 240,000 = 240,000` → bill in "1 thùng Pepsi - 240,000đ" (đúng ngữ nghĩa).

### cancel_invoice / cancel_goods_receipt

Hoàn toàn tương tự: dùng `conversion_rate` snapshot trên item để tính `base_qty`, bút toán ngược theo `base_qty`.

### Barcode search

`GET /products/barcode/{code}`:
1. Tìm trong `products.barcode` (as usual)
2. Nếu không tìm thấy → tìm trong `product_units.barcode`
3. Trả về product + `matched_unit` (null nếu barcode trỏ thẳng vào product)

```json
{
  "id": 1, "name": "Bia Sài Gòn", "unit": "lon",
  "matched_unit": {
    "id": 5, "unit_name": "thùng", "conversion_rate": 24, "sale_price": 240000
  }
}
```

### DELETE product_unit — Chặn nếu đang dùng

Không cho xóa unit nếu có DRAFT receipt/invoice đang dùng `unit_id` đó. COMPLETED transactions đã snapshot → không ảnh hưởng (ON DELETE SET NULL chỉ ảnh hưởng audit trail, không ảnh hưởng conversion_rate đã lưu).

---

## API Endpoints

### Product Units CRUD

```
GET    /api/v1/products/{id}/units           DS đơn vị quy đổi (trả về cùng GET /products/{id})
POST   /api/v1/products/{id}/units           Tạo đơn vị mới          [OWNER only]
PUT    /api/v1/products/{id}/units/{uid}     Sửa đơn vị              [OWNER only]
DELETE /api/v1/products/{id}/units/{uid}     Xóa đơn vị              [OWNER only]
```

**Body POST/PUT:**
```json
{
  "unit_name": "thùng",
  "conversion_rate": 24,
  "sale_price": 240000,       // null = product.sale_price × 24
  "barcode": "8934563012345"  // null nếu không có
}
```

### GET /products/{id} response

```json
{
  "id": 1, "name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000,
  "units": [
    {"id": 5, "unit_name": "thùng", "conversion_rate": 24, "sale_price": 240000, "barcode": "..."},
    {"id": 6, "unit_name": "lốc",   "conversion_rate": 6,  "sale_price": 65000,  "barcode": null}
  ]
}
```

### Goods Receipt item (request body)

```json
{
  "product_id": 1,
  "unit_id": 5,          // null = base unit
  "quantity": 2,         // 2 thùng
  "cost_price": 240000   // giá mỗi thùng; system tính cost_per_base = 240000 ÷ 24
}
```

### Invoice item (request body)

```json
{
  "product_id": 1,
  "unit_id": 5,           // null = base unit
  "quantity": 1,          // 1 thùng
  "unit_price": 240000    // giá mỗi thùng (override)
}
```

### GET /inventory response

```json
{
  "product_id": 1, "product_name": "Bia Sài Gòn",
  "unit": "lon", "quantity": 48,
  "units_breakdown": [
    {"unit_name": "thùng", "conversion_rate": 24, "quantity_in_unit": 2.0},
    {"unit_name": "lốc",   "conversion_rate": 6,  "quantity_in_unit": 8.0}
  ]
}
```

---

## Phân quyền

| Hành động | OWNER | CASHIER |
|-----------|-------|---------|
| Xem product units | ✅ | ✅ |
| Tạo/Sửa/Xóa product unit | ✅ | ❌ |
| Dùng unit khi nhập kho / bán hàng | ✅ | ✅ |

---

## Migration

Alembic migration cần thực hiện (theo thứ tự):

1. Tạo bảng `product_units` + indexes
2. `ALTER TABLE goods_receipt_items ADD COLUMN unit_id, unit_name, conversion_rate`
3. `ALTER TABLE invoice_items ADD COLUMN unit_id, conversion_rate`

Dữ liệu cũ không cần migrate (null unit_id = base unit, backward compatible).

---

## Audit

- `CREATE_PRODUCT_UNIT`, `UPDATE_PRODUCT_UNIT`, `DELETE_PRODUCT_UNIT` thêm vào action enum
- Ghi audit khi tạo/sửa/xóa product unit (OWNER only actions)

---

## CLAUDE.md Updates cần thiết

Sau khi implement, cập nhật CLAUDE.md:
- Thêm DDL `product_units` vào Phần 2
- Thêm columns mới vào DDL `goods_receipt_items` và `invoice_items`
- Cập nhật pseudocode `complete_goods_receipt` và `complete_invoice`
- Thêm endpoints product units vào API list
- Xóa yêu cầu 3 khỏi backlog (đã implement Phase 1)

---

## Out of scope (Phase 2)

- Product unit mặc định hiển thị trên POS (is_default_sale flag) — Phase 1 FE tự handle
- Báo cáo theo đơn vị quy đổi (thùng) — Phase 2
- Import Excel có cột đơn vị — Phase 2
