# Tài liệu nghiệp vụ (BA/SRS) — Hệ thống POS & Quản lý bán hàng kiểu KiotViet

> **Mục đích:** Đặc tả lại **toàn bộ nghiệp vụ** của một hệ thống bán lẻ kiểu KiotViet (phiên bản **Bán lẻ / tạp hóa – siêu thị mini**), dưới góc nhìn **Senior Business Analyst**, để làm nguồn tham chiếu (source of truth) cho việc bổ sung tính năng vào hệ thống `my_kiot`.
>
> **Phạm vi áp dụng:** Tạp hóa / siêu thị mini multi-tenant SaaS (xem `CLAUDE.md`). Các module đặc thù nhà hàng/F&B/spa/salon của KiotViet **không** nằm trong phạm vi.
>
> **Trạng thái ký hiệu:** ✅ Đã có trong MVP · 🟡 Có một phần / cần mở rộng · 🔴 Chưa có
>
> **Ngày tạo:** 2026-06-06 · **Tác giả:** Claude (BA) · **Phiên bản:** 1.0

---

## 0. Cách đọc tài liệu

- Mỗi module gồm: **Mục tiêu nghiệp vụ → Actor → Use case → Luồng chính → Business Rules (BR) → Dữ liệu → Trạng thái vs MVP**.
- **BR-x.y** = Business Rule có mã để truy vết khi implement.
- Mọi nguyên tắc kỹ thuật nền tảng (multi-tenant, soft-delete, DECIMAL tiền tệ, kardex append-only, tiếng Việt cho mọi message) **kế thừa nguyên văn từ `CLAUDE.md`** — tài liệu này **không lặp lại**, chỉ bổ sung phần nghiệp vụ KiotViet còn thiếu.

---

## 1. Tổng quan hệ thống & Đối tượng sử dụng

### 1.1 Bản đồ nghiệp vụ KiotViet (Retail)

```
┌─────────────────────────────────────────────────────────────────┐
│                        CỬA HÀNG (Tenant)                          │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│  HÀNG HÓA     │  GIAO DỊCH    │   ĐỐI TÁC     │     KHO          │
│  - SP/Nhóm    │  - Bán hàng   │  - Khách hàng │  - Nhập hàng     │
│  - Đơn vị     │  - Hóa đơn    │  - NCC        │  - Kiểm kho      │
│  - Bảng giá   │  - Trả hàng   │  - Công nợ    │  - Chuyển kho    │
│  - In tem     │  - Đặt hàng   │  - Tích điểm  │  - Xuất hủy      │
├───────────────┴───────────────┴───────────────┴─────────────────┤
│  SỔ QUỸ          │  KHUYẾN MÃI    │  NHÂN VIÊN      │  BÁO CÁO     │
│  - Phiếu thu/chi │  - CT giảm giá │  - Phân quyền   │  - Cuối ngày │
│  - Số dư quỹ     │  - Mua X tặng Y│  - Kết ca       │  - Đa chiều  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Actor (vai trò người dùng)

| Actor | Mô tả | MVP hiện tại |
|-------|-------|--------------|
| **Chủ cửa hàng (OWNER)** | Toàn quyền: cấu hình, báo cáo, duyệt hủy, sổ quỹ, khuyến mãi | ✅ |
| **Thu ngân (CASHIER)** | Bán hàng, nhập kho, tạo SP/KH cơ bản | ✅ |
| **Quản lý (MANAGER)** | 🔴 Trung gian: xem báo cáo + duyệt nghiệp vụ, không đụng cấu hình hệ thống | 🔴 KiotViet có, MVP chưa |
| **Nhân viên kho (STOCK)** | 🔴 Chuyên kiểm kho, nhập/xuất, không bán hàng | 🔴 Tùy chọn Phase 2 |

> **Quyết định scope:** MVP giữ 2 role. KiotViet thực tế cho phép **phân quyền chi tiết theo từng chức năng** (role-based + permission matrix). Đây là một hạng mục nâng cấp (xem §9).

---

## 2. MODULE HÀNG HÓA (Products) — mở rộng

### 2.1 Trạng thái
- ✅ CRUD SP, nhóm hàng 2 cấp, SKU/barcode, đơn vị quy đổi (`product_units`), giá vốn/giá bán.
- 🔴 Còn thiếu so với KiotViet: **bảng giá nhiều mức**, **in tem mã vạch**, **hàng theo lô–hạn sử dụng**, **combo/đóng gói**, **thuộc tính/biến thể**, **import Excel**.

### 2.2 UC-P09 — Bảng giá nhiều mức (Price Book) 🔴

**Mục tiêu:** 1 SP có thể có nhiều giá bán theo ngữ cảnh (giá lẻ, giá sỉ, giá thành viên, giá theo chi nhánh/khung giờ).

**Business Rules:**
- BR-P09.1: Mỗi tenant có ≥1 bảng giá; bảng giá `Chung` (default) luôn tồn tại, không xóa được.
- BR-P09.2: Bảng giá có thể giới hạn thời gian hiệu lực (`start_at`, `end_at`) và đối tượng áp dụng (nhóm KH).
- BR-P09.3: Khi bán, hệ thống chọn giá theo thứ tự ưu tiên: giá theo nhóm KH > bảng giá đang chọn > giá mặc định SP. Thu ngân vẫn được override thủ công trên dòng (đã hỗ trợ).
- BR-P09.4: Giá trong bảng giá là **snapshot vào invoice_item.unit_price** tại thời điểm bán.

**Dữ liệu mới:** `price_books`, `price_book_items (price_book_id, product_id, unit_id, price)`.

### 2.3 UC-P10 — In tem mã vạch (Barcode Label) 🔴

**Mục tiêu:** In tem EAN-13/Code-128 dán lên hàng (đặc biệt hàng cân, hàng không có barcode nhà SX).

**Luồng chính:** Chọn SP → chọn số lượng tem / khổ tem (e.g. 35×22mm, 50×30mm) → preview → in (PDF/trực tiếp máy in tem).

**Business Rules:**
- BR-P10.1: Tem hiển thị: tên SP (cắt ngắn), giá bán, mã vạch, SKU; tùy chọn ngày in / hạn dùng.
- BR-P10.2: Nếu SP chưa có barcode → sinh barcode nội bộ (Code-128 từ SKU).
- BR-P10.3: Khổ tem & nội dung cấu hình ở `tenants.settings.label_template`.

**Kỹ thuật FE:** sinh mã vạch bằng thư viện (vd JsBarcode) + layout in (CSS `@media print`), không cần BE phức tạp.

### 2.4 UC-P11 — Hàng theo lô & hạn sử dụng (Batch/Expiry) 🔴

**Mục tiêu:** Quản lý tồn theo lô + cảnh báo cận date — quan trọng với thực phẩm, sữa, đồ uống.

**Business Rules:**
- BR-P11.1: SP có cờ `track_batch=true` mới quản lý lô. SP thường giữ nguyên logic hiện tại.
- BR-P11.2: Nhập hàng SP có lô → bắt buộc nhập `batch_no` + `expiry_date`; tồn kho tách theo lô.
- BR-P11.3: Bán hàng theo nguyên tắc **FEFO** (hết hạn trước xuất trước) mặc định, cho phép chọn lô thủ công.
- BR-P11.4: Báo cáo cảnh báo hàng sắp hết hạn (ngưỡng cấu hình, vd ≤ 30 ngày).

**Dữ liệu mới:** `product_batches (product_id, batch_no, expiry_date, quantity)`; `stock_movements` thêm `batch_id`.

> ⚠️ **Độ phức tạp cao** — ảnh hưởng tới lõi tồn kho. Đề xuất tách thành dự án con riêng, làm sau các tính năng giao dịch.

### 2.5 UC-P12 — Combo / Đóng gói (Bundle) 🔴 *(ưu tiên thấp)*
SP combo = tập hợp SP con; khi bán combo → trừ tồn các SP con. Tạp hóa ít dùng → **Phase 2**.

### 2.6 UC-P13 — Import Excel (backlog #3) 🟡
Đã ghi trong backlog `CLAUDE.md`. Mức ưu tiên trung bình khi onboarding shop > 100 SP.

---

## 3. MODULE GIAO DỊCH — Bán hàng, Trả hàng, Đặt hàng

### 3.1 Bán hàng POS ✅ (đã có) — bổ sung nhỏ
- ✅ Giỏ hàng, quét barcode, thanh toán đa PT, treo bill, in nhiệt, bán nợ.
- 🟡 Bổ sung KiotViet-style: **chọn bảng giá** khi bán (BR-P09.3), **áp khuyến mãi tự động** (xem §8), **chọn lô** nếu SP track_batch (BR-P11.3).

### 3.2 UC-S11 — Trả hàng bán (Sales Return) 🔴 ⭐ **ưu tiên cao**

**Mục tiêu nghiệp vụ:** KH trả lại hàng đã mua → hoàn tiền (hoặc ghi có công nợ) + nhập lại tồn kho.

**Actor:** CASHIER tạo, OWNER duyệt nếu vượt ngưỡng (cấu hình).

**Luồng chính:**
1. Tìm hóa đơn gốc (`COMPLETED`) theo mã/SĐT KH.
2. Chọn các dòng + số lượng trả (≤ số lượng đã mua – đã trả trước đó).
3. Hệ thống tính tiền hoàn = Σ(line trả) – phí trả hàng (nếu có).
4. Chọn hình thức hoàn: tiền mặt / chuyển khoản / trừ công nợ / ghi có ví KH.
5. Hoàn tất → tạo phiếu trả `RETURN`, **nhập lại kho** (kardex `type=RETURN`), cập nhật công nợ/sổ quỹ.

**Business Rules:**
- BR-S11.1: Chỉ trả được hàng từ hóa đơn `COMPLETED`. Không trả vượt số đã mua (theo từng SP, trừ đi các lần trả trước).
- BR-S11.2: Giá hoàn = `invoice_item.unit_price` snapshot (không theo giá hiện tại).
- BR-S11.3: Nhập lại kho theo **đơn vị cơ bản** = `quantity × conversion_rate`, kardex `type=RETURN, ref_type=SALES_RETURN` (xem bảng enum §3.5).
- BR-S11.4: Giá vốn khi nhập trả lại: kardex ghi `unit_cost = invoice_item.cost_price` snapshot. **KHÔNG tính lại giá vốn bình quân** của SP (đây là hàng cũ quay về) — chấp nhận sai số nhỏ với `product.cost_price` hiện tại ở MVP (nhất quán với BR-I08.3).
- BR-S11.5: Cập nhật thống kê KH: `total_spent -= tiền_hoàn`, không giảm `total_orders`.
- BR-S11.6: Ghi sổ quỹ phiếu chi nếu hoàn tiền mặt/CK (liên kết §7); hoặc ghi giảm công nợ KH (§6.2) nếu hoàn vào nợ.
- BR-S11.7: ⭐ **Điều chỉnh báo cáo (BẮT BUỘC):** report doanh thu/lợi nhuận hiện tính trực tiếp trên `invoices.total`/`invoices.cost_total` (`report/service.py` — **không đọc kardex**). Vì vậy báo cáo PHẢI trừ giá trị hàng trả trong kỳ: `revenue -= Σ refund_amount`, `cost -= Σ (qty_trả × cost_price snapshot)`. Hạng mục sửa report này nằm **CHUNG scope** của tính năng Trả hàng (Đợt 1), không tách sang Đợt 2.
- BR-S11.8: Phiếu trả `COMPLETED` chỉ **OWNER** được hủy → bút toán ngược kardex `type=CANCEL_RETURN, ref_type=SALES_RETURN` + đảo lại sổ quỹ/công nợ/thống kê KH.
- BR-S11.9: Audit action mới `CREATE_SALES_RETURN` / `CANCEL_SALES_RETURN` (cần thêm vào Action enum chuẩn CLAUDE.md). Chỉ OWNER duyệt phiếu trả vượt `settings.return_approval_threshold`.
- BR-S11.10: Endpoint tạo phiếu trả tuân giải pháp **Idempotency-Key** (backlog #7 CLAUDE.md) khi triển khai, tránh hoàn tiền/nhập kho 2 lần do double-submit.

**Dữ liệu mới:** `return_orders` (≈ cấu trúc invoices, có `refund_amount`, `refund_method`), `return_order_items` (ref `invoice_item_id`, snapshot `unit_price`/`cost_price`).

### 3.5 Chuẩn hóa enum `stock_movements` cho các nghiệp vụ mới

> Enum gốc CLAUDE.md Phần 5: `type ∈ {SALE, RECEIPT, CANCEL_SALE, CANCEL_RECEIPT, ADJUSTMENT}`, `ref_type ∈ {INVOICE, GOODS_RECEIPT, MANUAL}`. Các nghiệp vụ mới bổ sung (mọi giá trị ≤ 20 ký tự, fit `String(20)`; **không có CHECK constraint** ở DB nên thêm an toàn). **Cần cập nhật bảng enum trong CLAUDE.md Phần 5.**

| Nghiệp vụ | `type` | `ref_type` | `ref_id` |
|-----------|--------|-----------|----------|
| Trả hàng bán | `RETURN` | `SALES_RETURN` | return_order_id |
| Hủy phiếu trả bán | `CANCEL_RETURN` | `SALES_RETURN` | return_order_id |
| Trả hàng nhập | `PURCHASE_RETURN` | `PURCHASE_RETURN` | purchase_return_id |
| Xuất hủy | `DISPOSAL` | `MANUAL` | user_id |

### 3.3 UC-S12 — Đặt hàng / Booking (Sales Order) 🔴 *(ưu tiên thấp cho tạp hóa)*
KH đặt trước, giao sau. Tạp hóa ít dùng → **Phase 2**. Ghi nhận để hoàn thiện bản đồ.

### 3.4 UC-S13 — Giao hàng (Delivery) 🔴 *(Phase 2)*
Quản lý vận đơn/đối tác giao hàng. Ngoài scope MVP tạp hóa.

---

## 4. MODULE NHẬP HÀNG — bổ sung

### 4.1 Phiếu nhập ✅ (đã có)
- ✅ Tạo/sửa nháp, complete (cộng tồn + giá vốn bình quân), kardex.

### 4.2 UC-I08 — Trả hàng nhập (Purchase Return) 🔴 ⭐ **ưu tiên cao**

**Mục tiêu:** Trả hàng lại NCC (hàng lỗi, cận date, dư) → giảm tồn + giảm công nợ phải trả NCC.

**Business Rules:**
- BR-I08.1: Trả từ phiếu nhập `COMPLETED`; số trả ≤ số đã nhập – đã trả.
- BR-I08.2: Xuất kho theo đơn vị cơ bản, kardex `type=PURCHASE_RETURN, ref_type=PURCHASE_RETURN` (xem §3.5), `unit_cost = goods_receipt_item.cost_price` snapshot.
- BR-I08.3: **Không** tính lại giá vốn bình quân (giảm tồn theo giá nhập snapshot là chấp nhận được ở MVP — nhất quán BR-S11.4).
- BR-I08.4: Giảm `suppliers.total_debt` nếu trước đó ghi nợ; hoặc tạo phiếu thu từ NCC (sổ quỹ §7).
- BR-I08.5: Chặn trả nếu tồn hiện tại < số muốn trả và SP không cho âm.
- BR-I08.6: Audit action `CREATE_PURCHASE_RETURN` (thêm vào enum chuẩn). Idempotency-Key như BR-S11.10.

**Dữ liệu mới:** `purchase_returns`, `purchase_return_items`.

### 4.3 UC-I09 — Đặt hàng nhập (Purchase Order) 🔴 *(ưu tiên thấp)*
Tạo đơn đặt NCC → khi hàng về convert thành phiếu nhập. **Phase 2**.

---

## 5. MODULE QUẢN LÝ KHO — bổ sung

### 5.1 Kiểm kho / Điều chỉnh tồn ✅ (đã có — `inventory/adjustments`)
- ✅ Kiểm kê, ghi `stock_movements type=ADJUSTMENT`.
- 🟡 Mở rộng KiotViet-style: **Phiếu kiểm kho có trạng thái DRAFT→BALANCED** (kiểm nhiều SP, lưu nháp, đối chiếu lệch rồi mới cân kho 1 lần) thay vì điều chỉnh tức thì.

### 5.2 UC-I10 — Phiếu kiểm kho (Stocktake Sheet) 🟡 **ưu tiên trung bình**

**Mục tiêu:** Kiểm kê toàn shop/theo nhóm — lưu nháp, nhập số đếm thực tế, hệ thống tính lệch, duyệt cân kho.

**Business Rules:**
- BR-I10.1: Phiếu kiểm có `system_qty` (tồn hệ thống lúc tạo) + `counted_qty` (đếm thực tế) → `diff`.
- BR-I10.2: Khi `BALANCED` → sinh 1 `stock_movement type=ADJUSTMENT` cho mỗi SP lệch ≠ 0.
- BR-I10.3: Chỉ OWNER cân kho. Audit `STOCK_ADJUSTMENT` với tổng giá trị lệch.

**Dữ liệu mới:** `stocktakes`, `stocktake_items`.

### 5.3 UC-I11 — Xuất hủy (Stock Disposal) 🔴 **ưu tiên trung bình**
Xuất hàng hỏng/hết hạn ra khỏi tồn (không bán). Kardex `type=DISPOSAL, ref_type=MANUAL`. Ghi giá trị thiệt hại vào báo cáo. Có thể gộp chung UI với điều chỉnh tồn (lý do = "Hỏng/Hết hạn").

### 5.4 UC-I12 — Chuyển kho (Stock Transfer) 🔴 *(Phase 2 — cần multi-warehouse)*
Phụ thuộc multi-warehouse (CLAUDE.md đã defer). **Phase 2**.

---

## 6. MODULE ĐỐI TÁC — Khách hàng & NCC nâng cao

### 6.1 ✅ CRUD KH/NCC, tìm theo SĐT, thống kê chi tiêu (đã có)

### 6.2 UC-C07 — Sổ công nợ KH & NCC 🔴 ⭐ **ưu tiên cao**

**Mục tiêu:** Theo dõi & thu/trả công nợ — DB đã có `paid_amount`, `total_debt` nhưng **chưa có module vận hành**.

**Business Rules:**
- BR-C07.1: Công nợ KH phát sinh khi `invoice.paid_amount < invoice.total` (bán nợ — cần `settings.allow_debt`).
- BR-C07.2: Công nợ NCC phát sinh khi `goods_receipt.paid_amount < total`.
- BR-C07.3: **Phiếu thu nợ KH** / **Phiếu trả nợ NCC** → cập nhật số dư nợ + ghi sổ quỹ (§7). Một phiếu thu có thể phân bổ cho **nhiều hóa đơn** (bảng `debt_allocations`); audit action `DEBT_PAYMENT`.
- BR-C07.4: Sổ công nợ là **append-only ledger** (`debt_entries`: +nợ khi bán nợ, −nợ khi thu) — số dư = SUM. Không sửa trực tiếp. `suppliers.total_debt` và cột **`customers.debt` (CẦN THÊM MỚI — hiện chưa có)** là **CACHE = SUM(debt_entries)**, cập nhật trong **cùng transaction** (đồng bộ đúng pattern `inventory` cache vs `stock_movements`).
- BR-C07.5: Báo cáo: danh sách KH/NCC còn nợ, tuổi nợ, lịch sử thanh toán.

**Dữ liệu mới:**
- `debt_entries (tenant_id, partner_type, partner_id, amount, ref_type, ref_id, balance_after, created_at)` — dùng chung KH & NCC (`partner_type ∈ {CUSTOMER, SUPPLIER}`).
- `debt_allocations (cash_transaction_id, invoice_id, amount)` — phân bổ 1 phiếu thu nợ cho nhiều hóa đơn.
- Thêm cột `customers.debt DECIMAL(15,2) DEFAULT 0` (cache).

### 6.3 UC-C08 — Nhóm khách hàng & Tích điểm/Hạng thành viên 🔴 **ưu tiên trung bình**

**Business Rules:**
- BR-C08.1: KH thuộc 1 nhóm (`customer_groups`); nhóm gắn với bảng giá (BR-P09.2) & % giảm mặc định.
- BR-C08.2: Tích điểm: mỗi hóa đơn `COMPLETED` cộng điểm = `total × tỉ_lệ_quy_đổi` (cấu hình). Trả hàng trừ điểm tương ứng.
- BR-C08.3: Dùng điểm: quy đổi điểm → tiền giảm trên hóa đơn (1 điểm = X đồng).
- BR-C08.4: Hạng thành viên theo tổng chi tiêu/điểm tích lũy (Bạc/Vàng/Kim cương) → ưu đãi.

**Dữ liệu mới:** `customer_groups`, `customers.group_id`, `customers.loyalty_points`, `loyalty_entries` (ledger).

---

## 7. MODULE SỔ QUỸ (Cashbook) 🔴 ⭐ **ưu tiên cao — mảng lớn còn thiếu hoàn toàn**

**Mục tiêu nghiệp vụ:** Quản lý dòng tiền mặt/ngân hàng của cửa hàng — KiotViet là module độc lập rất được dùng.

### 7.1 UC-F01 — Phiếu thu / Phiếu chi

**Luồng:** Tạo phiếu thu (tiền vào) / phiếu chi (tiền ra) → chọn loại thu-chi + đối tượng (KH/NCC/NV/khác) → số tiền + phương thức → lưu → cập nhật số dư quỹ.

**Business Rules:**
- BR-F01.1: Phiếu thu/chi có `type` (THU/CHI), `category` (loại: bán hàng, thu nợ, trả NCC, lương, tiền điện, khác), `method` (tiền mặt/CK), `amount`, `partner`.
- BR-F01.2: **Tự động sinh phiếu** từ nghiệp vụ khác: complete invoice tiền mặt → phiếu thu tự động; complete receipt trả tiền → phiếu chi; thu nợ/trả nợ → phiếu thu/chi (gắn cờ `auto_generated=true`, không sửa tay).
- BR-F01.3: Phiếu thủ công (lương, điện, nước…) do người dùng tạo.
- BR-F01.4: Số dư quỹ = số dư đầu kỳ + Σthu − Σchi. Báo cáo quỹ theo ngày/phương thức thanh toán (PTTT).
- BR-F01.5: **1 phiếu thu/chi = 1 PTTT** (`method` đơn trị). Nếu khách trả 1 hóa đơn bằng nhiều PTTT (đã hỗ trợ ở bảng `payments`) → sinh **nhiều phiếu thu**, mỗi phiếu 1 PTTT. (Quyết định này giữ `cash_transactions` đơn giản; nhất quán với khả năng đa PTTT của POS.)
- BR-F01.6: Chỉ OWNER (và MANAGER khi UC-A09 xong) tạo phiếu chi > ngưỡng. Audit action `CASH_RECEIPT` / `CASH_PAYMENT` (thêm vào enum chuẩn). Idempotency-Key như BR-S11.10.

> **Lưu ý role (Đợt 1–2):** Hệ thống hiện chỉ có **OWNER/CASHIER**. Mọi mệnh đề "MANAGER/STOCK nếu có" trong tài liệu coi như **OWNER** cho tới khi UC-A09 (phân quyền chi tiết, §9.2) hoàn thành.

**Dữ liệu mới:** `cash_transactions (tenant_id, code, type, category, method, amount, partner_type, partner_id, ref_type, ref_id, note, created_by, created_at)`.

### 7.2 UC-F02 — Báo cáo sổ quỹ
Số dư đầu/cuối kỳ, tổng thu, tổng chi, chi tiết theo loại — liên kết §10.

---

## 8. MODULE KHUYẾN MÃI (Promotions) 🔴 **ưu tiên trung bình** (CLAUDE.md để Phase 2)

**Mục tiêu:** Chương trình khuyến mãi tự động áp khi bán, thay cho giảm giá thủ công.

### 8.1 UC-PR01 — Chương trình khuyến mãi

**Loại KM (KiotViet):**
1. Giảm giá hóa đơn (theo % hoặc số tiền, ngưỡng tổng tiền).
2. Giảm giá sản phẩm/nhóm hàng.
3. Mua X tặng Y (quà tặng / SP khuyến mãi).
4. Giảm theo nhóm KH / hạng thành viên.

**Business Rules:**
- BR-PR01.1: CT có thời gian hiệu lực, điều kiện áp dụng (chi nhánh, nhóm KH, khung giờ), độ ưu tiên.
- BR-PR01.2: Khi bán, engine duyệt các CT đủ điều kiện theo ưu tiên, áp vào hóa đơn; thể hiện rõ dòng giảm giá.
- BR-PR01.3: Snapshot khuyến mãi đã áp vào hóa đơn (để báo cáo & không đổi khi CT hết hạn).
- BR-PR01.4: Cho phép cộng dồn hay loại trừ giữa các CT — cấu hình.

**Dữ liệu mới:** `promotions`, `promotion_conditions`, `promotion_rewards`, `invoice.promotion_snapshot`.

**MVP-scope Khuyến mãi (đóng khung để build nhất quán):**
- Chỉ làm **loại 1** (giảm bill theo ngưỡng tổng tiền) + **loại 2** (giảm SP/nhóm hàng). Loại 3 (mua X tặng Y) & loại 4 (theo nhóm KH) → Phase sau.
- **1 CT áp tại 1 thời điểm — KHÔNG cộng dồn** (chọn CT ưu tiên cao nhất đủ điều kiện).
- **Thứ tự áp giá cố định:** bảng giá (§2.2) → khuyến mãi tự động → discount thủ công trên dòng/bill (đã có). Mỗi tầng ghi snapshot riêng vào hóa đơn.

> ⚠️ Promotion engine phức tạp; làm **sau** nhóm ưu tiên cao (Đợt 3).

---

## 9. MODULE NHÂN VIÊN, PHÂN QUYỀN & KẾT CA

### 9.1 ✅ Quản lý NV cơ bản (mời, khóa, 2 role) — đã có

### 9.2 UC-A09 — Phân quyền chi tiết (Permission Matrix) 🔴 **ưu tiên trung bình**
KiotViet cho phép bật/tắt **từng quyền** theo vai trò (xem báo cáo, sửa giá vốn, hủy hóa đơn, sổ quỹ…). Nâng cấp từ 2 role cứng → role + bảng quyền.

**Dữ liệu mới:** `roles`, `permissions`, `role_permissions`, `users.role_id`. Giữ backward-compat với OWNER/CASHIER.

### 9.3 UC-A10 — Kết ca / Chốt cuối ngày (Shift / End-of-day) 🔴 ⭐ **ưu tiên cao** (backlog #5)

**Mục tiêu:** Thu ngân mở ca (tiền đầu ca) → bán → cuối ca đối chiếu tiền mặt thực tế vs hệ thống → chốt ca.

**Business Rules:**
- BR-A10.1: 1 ca = (mở ca → đóng ca) của 1 thu ngân (branch mặc định = 1 ở MVP; "chi nhánh" mở khóa khi multi-branch Phase 2). Mọi hóa đơn/phiếu thu-chi gắn `shift_id`. Audit `OPEN_SHIFT` / `CLOSE_SHIFT`.
- BR-A10.2: Mở ca nhập `opening_cash`. Đóng ca nhập `counted_cash` → hệ thống tính `expected_cash = opening + thu_TM − chi_TM` và `lệch = counted − expected`.
- BR-A10.3: Báo cáo kết ca: doanh thu ca, số HĐ, tiền theo PT thanh toán, lệch quỹ.
- BR-A10.4: Không cho mở 2 ca cùng lúc cho 1 thu ngân.

**Dữ liệu mới:** `pos_sessions (tenant_id, cashier_id, opening_cash, expected_cash, counted_cash, diff, opened_at, closed_at, status)`; FK `shift_id` thêm vào `invoices`, `cash_transactions`.

---

## 10. MODULE BÁO CÁO — mở rộng đa chiều

### 10.1 ✅ Đã có: dashboard, doanh thu, lợi nhuận, top SP, tồn kho.

### 10.2 Báo cáo bổ sung KiotViet 🔴/🟡
| Mã | Báo cáo | Ưu tiên | Phụ thuộc |
|----|---------|---------|-----------|
| UC-R07 | **Báo cáo cuối ngày / kết ca** | Cao | §9.3 |
| UC-R08 | **Báo cáo công nợ KH/NCC** | Cao | §6.2 |
| UC-R09 | **Báo cáo sổ quỹ / dòng tiền** | Cao | §7 |
| UC-R10 | Báo cáo bán hàng theo nhân viên | TB | shift/cashier |
| UC-R11 | Báo cáo trả hàng (bán & nhập) | TB | §3.2, §4.2 |
| UC-R12 | Báo cáo hàng cận/hết hạn | TB | §2.4 |
| UC-R13 | Báo cáo khách hàng (mua nhiều, tích điểm) | Thấp | §6.3 |
| UC-R14 | Sổ chi tiết bán hàng / xuất nhập tồn theo SP | TB | kardex (đã có) |

**BR chung báo cáo:** filter theo khoảng ngày + chi nhánh; tiền theo timezone `Asia/Ho_Chi_Minh` (kế thừa CLAUDE.md); export Excel/PDF (tùy chọn).

---

## 11. THIẾT LẬP HỆ THỐNG (Settings) — mở rộng

- 🟡 Mở rộng `tenants.settings`: `label_template` (in tem), `loyalty_rate`, `default_price_book_id`, `return_approval_threshold`, `cash_categories[]`.
- 🔴 **Mẫu in hóa đơn** tùy biến (logo, header/footer, khổ K57/K80) — KiotViet cho sửa template. MVP đang fix cứng `receipt_footer`.
- 🔴 **Quản lý chi nhánh** (multi-branch) — gắn với multi-warehouse Phase 2.

---

## 12. Yêu cầu phi chức năng (kế thừa CLAUDE.md)

Multi-tenant isolation · BIGSERIAL PK · DECIMAL(15,2) tiền · soft-delete · kardex append-only · **mọi message tiếng Việt** · JWT + refresh rotation · audit_logs cho mọi mutation · partial unique index · timezone TZ-aware. **Mọi tính năng mới trong tài liệu này phải tuân thủ y nguyên các nguyên tắc đó** (xem checklist §13).

---

## 13. BẢNG TỔNG HỢP GAP & ROADMAP ƯU TIÊN

### 13.1 Ma trận gap

| # | Tính năng | Module | Trạng thái | Ưu tiên | Độ phức tạp | Phụ thuộc |
|---|-----------|--------|-----------|---------|-------------|-----------|
| 1 | Trả hàng bán | Giao dịch | 🔴 | ⭐ Cao | TB | Hóa đơn (có) |
| 2 | Sổ quỹ (thu/chi) | Sổ quỹ | 🔴 | ⭐ Cao | TB | — |
| 3 | Công nợ KH & NCC | Đối tác | 🔴 | ⭐ Cao | TB | Hóa đơn, Phiếu nhập (có) |
| 4 | Kết ca / cuối ngày | Nhân viên | 🔴 | ⭐ Cao | TB | Sổ quỹ (#2) |
| 5 | Trả hàng nhập | Nhập hàng | 🔴 | ⭐ Cao | TB | Phiếu nhập (có) |
| 6 | In tem mã vạch | Hàng hóa | 🔴 | TB | Thấp (FE) | — |
| 7 | Phiếu kiểm kho | Kho | 🟡 | TB | TB | Adjustment (có) |
| 8 | Xuất hủy | Kho | 🔴 | TB | Thấp | kardex (có) |
| 9 | Bảng giá nhiều mức | Hàng hóa | 🔴 | TB | TB | — |
| 10 | Khuyến mãi | Khuyến mãi | 🔴 | TB | Cao | bán hàng |
| 11 | Nhóm KH & tích điểm | Đối tác | 🔴 | TB | TB | bảng giá (#9) |
| 12 | Phân quyền chi tiết | Nhân viên | 🔴 | TB | TB | — |
| 13 | Hàng theo lô–HSD | Hàng hóa | 🔴 | TB | Cao | lõi tồn kho |
| 14 | Báo cáo mở rộng | Báo cáo | 🔴 | theo #1–4 | Thấp–TB | các module trên |
| 15 | Import Excel SP | Hàng hóa | 🟡 | Thấp | TB | — |
| 16 | Combo/đóng gói | Hàng hóa | 🔴 | Thấp | TB | — |
| 17 | Đặt hàng (bán/nhập) | Giao dịch | 🔴 | Thấp | TB | — |
| 18 | Multi-branch / chuyển kho | Kho | 🔴 | Phase 2 | Cao | multi-warehouse |
| 19 | Mẫu in hóa đơn tùy biến | Settings | 🔴 | Thấp | Thấp | — |

### 13.2 Lộ trình đề xuất (thứ tự build với `/kiot-feature`)

**Đợt 1 — Lõi tài chính & giao dịch (giá trị cao nhất, ít phụ thuộc):**
1. **Sổ quỹ (thu/chi)** — nền tảng dòng tiền, nhiều module sau móc vào.
2. **Công nợ KH & NCC** — tận dụng `paid_amount`/`total_debt` sẵn có; ghi phiếu thu/chi vào sổ quỹ.
3. **Trả hàng bán** — nghiệp vụ hằng ngày; móc vào kho + sổ quỹ + công nợ.
4. **Trả hàng nhập** — đối xứng #3.

**Đợt 2 — Vận hành cửa hàng:**
5. **Kết ca / chốt cuối ngày** — cần sổ quỹ (Đợt 1).
6. **In tem mã vạch** — độc lập, nhanh, FE-heavy.
7. **Xuất hủy + Phiếu kiểm kho** — hoàn thiện nghiệp vụ kho.
8. **Báo cáo mở rộng (R07–R09, R11)** — phản ánh các nghiệp vụ Đợt 1–2.

**Đợt 3 — Marketing & giá:**
9. **Bảng giá nhiều mức** → 10. **Nhóm KH & tích điểm** → 11. **Khuyến mãi**.

**Đợt 4 — Nâng cao / Phase 2:**
12. Phân quyền chi tiết · 13. Hàng theo lô–HSD · 15. Import Excel · 16–19 còn lại.

### 13.3 Checklist bắt buộc cho MỖI tính năng mới (kế thừa §"Migration checklist" CLAUDE.md)
1. Alembic migration cho bảng + index mới.
2. Partial unique index test soft-delete (nếu có mã/unique).
3. Mọi query filter `tenant_id`.
4. Mọi mutation ghi `audit_logs`.
5. Endpoint mutation `require_role` đúng.
6. ≥1 test "tenant A không thấy data tenant B".
7. **Nếu** thay đổi giá/cost → ghi `price_history` (trả hàng/sổ quỹ/công nợ không đổi giá → bỏ qua).
8. Mọi message người dùng **tiếng Việt** (memory: `feedback_vietnamese_errors`).
9. FE: trang + route + store + gọi API qua `api/client.ts`.
10. **Action enum mới** (bổ sung vào CLAUDE.md §Audit khi build): `CREATE_SALES_RETURN`, `CANCEL_SALES_RETURN`, `CREATE_PURCHASE_RETURN`, `STOCK_DISPOSAL`, `CASH_RECEIPT`, `CASH_PAYMENT`, `DEBT_PAYMENT`, `OPEN_SHIFT`, `CLOSE_SHIFT`.
11. **Enum `stock_movements` mới** (§3.5): cập nhật CLAUDE.md Phần 5.

---

## 14. Câu hỏi mở cần chủ shop quyết (trước khi build)

1. Có bán nợ không? (bật `allow_debt`) → quyết định độ ưu tiên Công nợ.
2. Có cần kết ca không, hay 1 ngày = 1 ca đối chiếu tay? (ảnh hưởng #4)
3. Khuyến mãi: cần engine đầy đủ hay chỉ giảm giá thủ công (đã có)?
4. Hàng theo lô–HSD: có bán hàng thực phẩm cận date nhiều không?
5. Có kế hoạch nhiều chi nhánh không? (mở khóa multi-warehouse Phase 2)

---

> **Ghi chú cho phiên làm việc tiếp theo:** Tài liệu này là đầu vào cho việc build từng tính năng bằng skill `/kiot-feature`. Bắt đầu từ **Đợt 1 mục #1 (Sổ quỹ)** trừ khi chủ shop chỉ định khác. Mỗi tính năng đi qua chu trình của `/kiot-feature`: research nghiệp vụ → plan → review plan → implement → UI → code-review → test loop.
