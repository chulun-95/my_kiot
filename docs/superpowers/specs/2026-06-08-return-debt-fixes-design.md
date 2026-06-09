# Spec — Sửa 2 lỗi nghiệp vụ nghiêm trọng quanh Trả hàng & Hủy hóa đơn

**Ngày:** 2026-06-08
**Phạm vi:** backend (sales, inventory/report), migration, tests
**Bối cảnh:** Phân tích nghiệp vụ phát hiện 2 lỗi 🔴 ở giao thoa giữa module Trả hàng (returns), Hủy hóa đơn và Báo cáo công nợ (derived debt).

---

## Lỗi #1 — Hủy hóa đơn đã có phiếu trả hàng làm sai tồn kho & thống kê

### Hiện trạng
`cancel_invoice` (COMPLETED → CANCELLED) cộng lại **toàn bộ** số lượng hóa đơn vào tồn kho và đảo `customer.total_spent` theo `invoice.total`. Nếu hóa đơn đã phát sinh `ReturnOrder` (đã cộng kho + hoàn tiền ở `create_return`), hàng bị cộng kho 2 lần và thống kê khách bị đảo 2 lần.

### Quyết định (đã chốt với user)
**Chặn** hủy hóa đơn nếu còn phiếu trả hàng ACTIVE. Buộc OWNER hủy các phiếu trả trước.

### Thiết kế
Trong `cancel_invoice` (`backend/modules/sales/service.py`), nhánh xử lý hóa đơn `COMPLETED`, **trước** khi đảo bút toán: truy vấn `ReturnOrder` thuộc hóa đơn này có `status == "COMPLETED"` (chưa hủy). Nếu tồn tại → ném:

```
AppError(400, "INVOICE_HAS_RETURNS",
  "Hóa đơn đã có phiếu trả hàng. Vui lòng hủy các phiếu trả trước khi hủy hóa đơn.",
  {"return_codes": [...]})
```

Hóa đơn `DRAFT` không bị ảnh hưởng (không thể có phiếu trả). Không sửa logic kho/quỹ hiện có.

---

## Lỗi #2 — Trả hàng trên đơn còn nợ luôn chi tiền mặt, không cấn trừ công nợ

### Hiện trạng
`create_return` luôn ghi `cash OUT = total_refund` bất kể hóa đơn đã trả đủ tiền hay chưa. Đơn bán nợ (`paid_amount < total`) khi trả hàng sẽ bị **chi tiền mặt cho khách dù khách chưa trả**, và công nợ (`customer_debts = Σ(total − paid) − Σ DEBT_COLLECTION`) **không giảm**.

### Quyết định (đã chốt — theo KiotViet)
KiotViet dùng **một sổ "nợ cần thu" hợp nhất** mỗi khách: giá trị trả hàng **cấn trừ thẳng vào công nợ** trước, chỉ phần dư mới chi tiền mặt ("tổng bán trừ trả hàng").

### Thiết kế

**Dữ liệu** — thêm 2 cột vào `return_orders`:
- `debt_adjust DECIMAL(15,2) NOT NULL DEFAULT 0` — phần giá trị trả hàng cấn vào công nợ (không chi tiền).
- `cash_refund DECIMAL(15,2) NOT NULL DEFAULT 0` — tiền mặt thực chi ra (`= total_refund − debt_adjust`).

Bất biến: `total_refund = debt_adjust + cash_refund`.

**Migration:** `alembic/versions/007_return_debt_adjust.py` add 2 cột (server_default "0"). Tests dùng `Base.metadata.create_all` nên chỉ cần thêm cột trong model.

**Logic `create_return`:**
1. Tính `total_refund` như hiện tại (giá trị hàng trả, theo `line_total` đã gồm chiết khấu dòng).
2. Nếu `invoice.customer_id` không null → tính **công nợ hiện tại của khách** `current_debt` (helper dùng cùng công thức báo cáo, đã trừ các `debt_adjust` của phiếu trả ACTIVE trước đó). Khách vãng lai → `current_debt = 0`.
3. `debt_adjust = min(total_refund, max(0, current_debt))`.
4. `cash_refund = total_refund − debt_adjust`.
5. Lưu `ro.debt_adjust`, `ro.cash_refund`.
6. Cashbook `REFUND (OUT)` ghi **`cash_refund`** (record_cash_entry tự bỏ qua nếu ≤ 0 → hết phantom cash).
7. `customer.total_spent −= total_refund` (giữ nguyên — "tổng bán trừ trả hàng").

**Helper tính công nợ hiện tại (`return_service._current_customer_debt`):**
```
owed     = Σ(invoice.total − paid_amount)  [COMPLETED, customer_id = cid]
collected = Σ cash IN  [ACTIVE, DEBT_COLLECTION, partner CUSTOMER = cid]
returned  = Σ ReturnOrder.debt_adjust [status COMPLETED, customer_id = cid]
current_debt = owed − collected − returned
```

**Báo cáo `customer_debts` (`report/service.py`):** trừ thêm `Σ ReturnOrder.debt_adjust` (status COMPLETED) theo từng khách vào công thức nợ.

**`cancel_return`:** không cần bút toán riêng cho phần debt. Khi `status` chuyển `COMPLETED → CANCELLED`, phiếu tự loại khỏi `Σ debt_adjust` (công nợ tự phục hồi). Phần `cash_refund` được `cancel_entries_for_ref` đảo ngược như cũ. `customer.total_spent += total_refund` giữ nguyên.

**Schema response:** thêm `debt_adjust`, `cash_refund` vào `ReturnResponse` để FE minh bạch.

---

## Test (pytest, sqlite in-memory)

**Lỗi #1:**
- Đơn COMPLETED có phiếu trả ACTIVE → `POST /invoices/{id}/cancel` trả 400 `INVOICE_HAS_RETURNS`.
- Sau khi hủy phiếu trả → hủy hóa đơn thành công, tồn kho đúng (không cộng đôi).
- Đơn không có phiếu trả → hủy bình thường.

**Lỗi #2:**
- Đơn nợ total 60k, paid 0, trả hàng 24k → `debt_adjust=24k`, `cash_refund=0`, không có phiếu chi tiền mặt; `customer_debts` còn 36k.
- Đơn nợ total 60k, paid 50k (nợ 10k), trả 24k → `debt_adjust=10k`, `cash_refund=14k`; nợ về 0.
- Đơn trả đủ tiền (paid=total), trả 24k → `debt_adjust=0`, `cash_refund=24k` (giữ hành vi cũ — không hồi quy).
- Hủy phiếu trả đơn nợ → công nợ & quỹ về trạng thái trước.

---

## Bổ sung đợt 2 (đã làm cùng lần này)

**Lỗi #3 — Trả hàng phân bổ chiết khấu toàn hóa đơn**
`create_return` tính `order_ratio = invoice.total / invoice.subtotal` và nhân vào mỗi `line_refund` → hoàn đúng phần khách thực trả, không hoàn dư khi đơn có chiết khấu tổng. Test: đơn 60k CK 6k (ratio 0.9), trả 2 món → hoàn 21.6k thay vì 24k.

**Lỗi #4 — CASHIER không thấy giá vốn ở màn Tồn kho**
`InventoryItemResponse.cost_price` đổi sang `Optional`; [inventory/router.py](../../../backend/modules/inventory/router.py) dùng `can_see_cost(...)` set `cost_price=None` cho CASHIER (trừ khi `tenant.settings.show_cost_to_cashier=true`). Đồng bộ với module product. Test: owner thấy 9000, cashier thấy None nhưng vẫn thấy quantity + sale_price.

## Không làm (out of scope — spec sau)
- Race insert tồn (ON CONFLICT), idempotency complete invoice, method thanh toán phiếu nhập, lệch timezone cashbook, dashboard role cho cashier, cột `suppliers.total_debt` chết — mỗi cái cần đổi schema/quyết định riêng.
