# Bán hàng offline trên Android — Thiết kế (local-first + sync thủ công)

> Ngày: 2026-06-21 · Nhánh đề xuất: `feat/android-offline-sales`
> Trạng thái: Spec đã chốt các quyết định, chờ review trước khi lập plan.

## 1. Mục tiêu & bối cảnh

App Android hiện **online thuần**: mọi thao tác POS (tìm SP, quét barcode, checkout) gọi API trực tiếp; server giữ toàn bộ logic (sinh mã `HD`, khóa & trừ tồn, giá vốn bình quân, sổ quỹ). Khi mất mạng, **không bán được**.

Mục tiêu: **khi mất mạng vẫn bán được hàng** (thu ngân quầy tạp hóa), đơn được lưu trên máy và **đẩy lên server khi có mạng**.

### Quyết định đã chốt (qua brainstorming)

| # | Quyết định | Chọn |
|---|-----------|------|
| 1 | Phạm vi offline | **Chỉ bán hàng + thanh toán** (tiền mặt/CK) cho **khách vãng lai**. KHÔNG bán nợ, KHÔNG gán/thêm khách, KHÔNG nhập kho/trả hàng/điều chỉnh khi offline. |
| 2 | Mô hình | **Local-first luôn luôn** — mọi đơn ghi xuống DB máy trước, sync ngầm sau. Một luồng duy nhất online/offline. |
| 3 | Conflict tồn kho khi sync | **Server LUÔN nhận** đơn offline, **cho phép âm tồn**, gắn cờ để chủ shop có danh sách "đơn làm âm tồn" đối chiếu. |
| 4 | Mã bill offline | **Mã tạm có đánh dấu** (in trên bill). Server sinh mã `HD` thật lúc sync và lưu liên kết mã tạm ↔ mã thật. |
| 5 | Kích hoạt sync | **Tự đẩy ngầm khi đang online** (sau mỗi đơn + khi app vào foreground / có mạng lại) — đúng tinh thần "sync định kỳ" của yêu cầu gốc. **Nút "Đồng bộ ngay"** (hiển thị số đơn chưa sync) là cơ chế dự phòng/thủ công. ✅ Đã chốt. |

### Ngoài phạm vi (Phase sau)

- Bán nợ / gán khách hàng khi offline (cần map id tạm ↔ id server).
- Nhập kho / trả hàng / điều chỉnh tồn offline.
- Đồng bộ tồn kho realtime giữa nhiều máy.
- Treo đơn (DRAFT) khi offline — offline chỉ bán đứt rồi in.

## 2. Kiến trúc tổng thể

```
┌─────────────── Android (local-first) ───────────────┐
│  POS  ─ tìm SP / quét barcode ──▶ ĐỌC Room (catalog cache)   (chạy cả khi offline)
│       ─ thanh toán ─────────────▶ GHI Room: offline_sale (PENDING) + in bill mã TẠM
│                                                       │
│  SyncManager ── nút "Đồng bộ ngay (n)" / tự đẩy khi online
│  CatalogCache ── kéo & làm mới catalog khi có mạng
└──────────────────────────────────────────┼───────────┘
                                            ▼  HTTPS (khi có mạng)
                          ┌──────────── Backend (FastAPI) ───────────┐
                          │  GET  /products/catalog?since=   (kéo catalog delta)
                          │  POST /invoices/offline-sync     (nhận batch đơn, idempotent)
                          │     → tạo Invoice COMPLETED trực tiếp, cho âm tồn,
                          │       sinh mã HD thật (theo NGÀY BÁN), ghi sổ quỹ,
                          │       map client_uuid/temp_code ↔ invoice_id/code
                          │  GET  /reports/offline-negative   (đơn offline làm âm tồn)
                          └───────────────────────────────────────────┘
```

**Ba trụ cột:**

1. **Catalog cache (Room)** — bản sao SP + đơn vị quy đổi để tìm/quét offline. POS **luôn đọc từ cache** (online & offline) → một luồng duy nhất, tìm tức thì. Cache làm mới khi có mạng.
2. **Outbox (Room)** — mỗi đơn bán là 1 `offline_sale` (PENDING). Khóa chống trùng = `client_uuid` (UUID sinh trên máy).
3. **SyncManager** — đẩy outbox lên `/invoices/offline-sync`, nhận mã thật, cập nhật trạng thái, phát luồng "số đơn chưa sync".

**Vì sao đọc catalog từ cache cả khi online:** giữ một luồng duy nhất (đúng tinh thần local-first), code POS không phân nhánh, tìm kiếm tức thì. Đánh đổi: giá/SP mới có độ trễ tới lần cập nhật catalog gần nhất — chấp nhận được với tạp hóa, và đã chốt conflict policy "luôn nhận".

## 3. Thay đổi Backend

### 3.1 Migration `invoices` (Alembic)

Thêm cột (đều nullable, không phá dữ liệu cũ):

| Cột | Kiểu | Ý nghĩa |
|-----|------|---------|
| `client_uuid` | `UUID NULL` | Khóa idempotency do máy sinh. `NULL` cho đơn online cũ. |
| `origin` | `VARCHAR(10) NOT NULL DEFAULT 'ONLINE'` | `ONLINE` \| `OFFLINE`. |
| `offline_temp_code` | `VARCHAR(30) NULL` | Mã tạm đã in trên bill ở máy. |
| `device_id` | `VARCHAR(64) NULL` | Định danh thiết bị bán (truy vết). |

Index:
```sql
CREATE UNIQUE INDEX uq_invoices_tenant_client_uuid
  ON invoices (tenant_id, client_uuid) WHERE client_uuid IS NOT NULL;
```
→ Đảm bảo retry/đẩy lại cùng đơn KHÔNG tạo trùng (idempotent ở tầng DB).

### 3.2 `GET /products/catalog?since=<ISO8601>`

Xuất catalog cho cache offline. Trả **toàn bộ SP ACTIVE** (+ đơn vị quy đổi) của tenant; nếu có `since` → chỉ trả SP có `updated_at > since` (delta sync, nhẹ).

Response (rút gọn — chỉ field POS cần; **không trả `cost_price`** để tránh lộ giá vốn cho CASHIER theo `show_cost_to_cashier`):
```jsonc
{
  "server_time": "2026-06-21T03:00:00Z",   // mốc cho lần since kế tiếp
  "items": [
    {
      "id": 12, "sku": "SP000012", "barcode": "8934...",
      "name": "Coca 330ml", "unit": "lon", "sale_price": "10000",
      "status": "ACTIVE",
      "units": [
        {"id": 5, "unit_name": "thùng", "conversion_rate": "24",
         "sale_price": "230000", "barcode": "8935..."}
      ]
    }
  ],
  "deleted_ids": [7, 9]   // SP đã soft-delete/INACTIVE từ `since` → máy xóa khỏi cache
}
```
Phân trang nội bộ nếu cần (server lặp), nhưng response gói gọn cho client tải 1 mạch. Quyền: mọi user đăng nhập (OWNER + CASHIER).

### 3.3 `POST /invoices/offline-sync` (batch, idempotent)

Nhận **nhiều đơn offline đã hoàn tất** trong 1 request. Mỗi đơn xử lý độc lập trong **transaction riêng** → một đơn lỗi không kéo cả batch.

Request:
```jsonc
{
  "device_id": "android-abc123",
  "sales": [
    {
      "client_uuid": "0f9c…",            // idempotency key
      "temp_code": "TM-abc123-000042",   // mã tạm đã in
      "sold_at": "2026-06-21T02:15:30Z", // thời điểm bán thực (giờ máy)
      "discount_amount": "0",
      "items": [
        {"product_id": 12, "unit_id": null, "quantity": "2",
         "unit_price": "10000", "discount_amount": "0"}
      ],
      "payments": [{"method": "CASH", "amount": "20000"}]
    }
  ]
}
```

Response — map từng đơn để máy cập nhật trạng thái:
```jsonc
{
  "results": [
    {"client_uuid": "0f9c…", "status": "SYNCED",
     "invoice_id": 501, "code": "HD20260621-077", "caused_negative": true},
    {"client_uuid": "1a2b…", "status": "FAILED",
     "error_code": "PRODUCT_NOT_FOUND", "error_message": "SP id=99 không tồn tại"}
  ]
}
```

**Logic mỗi đơn** (mô phỏng `complete_invoice` nhưng tạo thẳng COMPLETED):

1. **Idempotency**: `SELECT invoice WHERE tenant_id, client_uuid`. Nếu có → trả luôn `{SYNCED, invoice_id, code}`, không tạo lại.
2. **Validate SP**: dùng `_validate_products`. SP không tồn tại (catalog drift) → `FAILED / PRODUCT_NOT_FOUND`, đơn vẫn nằm outbox để chủ xử lý tay.
3. **Sinh mã**: `generate_code(prefix='HD')` **theo ngày của `sold_at`** (giờ VN) — để mã phản ánh ngày bán, không phải ngày sync. *(Cần biến thể `generate_code` nhận `when: datetime`.)*
4. **Tạo Invoice** `status='COMPLETED'`, `origin='OFFLINE'`, `client_uuid`, `offline_temp_code`, `device_id`, `customer_id=NULL`, `completed_at = sold_at`, `created_at = sold_at`.
5. **Tính dòng** bằng `_compute_line` (snapshot `cost_price = product.cost_price` **tại thời điểm sync** — chấp nhận theo thiết kế).
6. **Lock tồn** `_lock_inventory_rows`. **BỎ QUA kiểm tra shortage** (offline luôn nhận) → trừ tồn kể cả âm. Đánh dấu `caused_negative = (new_balance < 0)` cho ≥1 dòng.
7. **Ghi kardex** `StockMovement type='SALE', ref_type='INVOICE'`, `balance_after` (có thể âm).
8. **Payments + sổ quỹ**: lưu `Payment`, gọi `cash_service.record_cash_entry` IN cho từng payment; nếu `paid > total` → chi `CHANGE`. (Giống `complete_invoice` bước 6/6b.)
9. **Audit** `COMPLETE_INVOICE` + `new_data.origin='OFFLINE'`.
10. **Commit** transaction đơn đó. Lỗi không lường (exception) → rollback đơn đó, trả `FAILED / SYNC_ERROR`, giữ outbox.

> Không cập nhật thống kê KH (khách vãng lai). Không validate debt (offline = trả đủ tiền mặt/CK).

### 3.4 `GET /reports/offline-negative` (OWNER only)

Danh sách đơn `origin='OFFLINE'` đã làm tồn âm (join `stock_movements.balance_after < 0` hoặc cờ lưu sẵn) để chủ shop kiểm kho/điều chỉnh. Tối thiểu: mã HD, mã tạm, thời điểm bán, các SP bị âm + số âm. *(Có thể gộp vào màn cảnh báo tồn hiện có; chốt khi làm UI.)*

## 4. Thay đổi Android

### 4.1 Phụ thuộc mới (`build.gradle.kts` + version catalog)

- `androidx.room:room-runtime`, `room-ktx`, `room-compiler` (ksp). DB cục bộ.
- (Tùy chọn) `androidx.datastore:datastore-preferences` cho mốc `catalog_last_synced` & `device_id`. Có thể dùng luôn `EncryptedSharedPreferences` đã có (`security.crypto`).

### 4.2 Room schema (`core/offline/db/`)

```
OfflineDb (RoomDatabase)
├── CachedProductDao / CachedProductEntity
│     id, sku, barcode?, name, unit, salePrice, status        (catalog cache)
├── CachedUnitDao / CachedUnitEntity
│     id, productId, unitName, conversionRate, salePrice?, barcode?
├── OfflineSaleDao / OfflineSaleEntity
│     clientUuid(PK), tempCode, soldAt, customerNull, subtotal,
│     discount, total, paidAmount, changeAmount, paymentsJson,
│     status(PENDING|SYNCING|SYNCED|FAILED), serverInvoiceId?, serverCode?,
│     errorCode?, errorMessage?, retryCount, syncedAt?
└── OfflineSaleItemDao / OfflineSaleItemEntity
      id, saleUuid(FK), productId, unitId?, name, sku, unit,
      unitPrice, quantity, discount, lineTotal, conversionRate?
```

- **Tìm SP / barcode offline**: query `CachedProductEntity` (LIKE name/sku, exact barcode) + `CachedUnitEntity.barcode` để quét barcode đơn vị (thùng/lốc) ra đúng SP + `matchedUnit`.
- **Snapshot trên `OfflineSaleItem`**: name/sku/unit/price/conversion_rate lưu cứng tại thời điểm bán — không phụ thuộc catalog sau này.

### 4.3 Catalog cache (`core/offline/CatalogCache.kt`)

- `refresh()` — gọi `GET /products/catalog?since=<last>`, upsert vào Room, xóa `deleted_ids`, lưu `server_time` làm `last`. Gọi khi: đăng nhập thành công, mở POS (nếu online & cache cũ > N phút), và trong `SyncManager.syncNow()`.
- Cờ "cache rỗng/quá cũ" → nếu chưa từng tải catalog mà mất mạng, POS hiện cảnh báo "Chưa tải dữ liệu để bán offline" (ErrorDialog theo convention dự án).

### 4.4 Outbox + SyncManager (`core/offline/`)

- `OfflineSaleRepository` — `enqueue(cart, payments)`: tính tiền cục bộ, sinh `client_uuid` (UUID) + `tempCode` (`TM-<deviceShort>-<seq>`, seq cục bộ tăng dần), ghi `OfflineSaleEntity(PENDING)` + items. Trả về dữ liệu để in bill ngay.
- `SyncManager`:
  - `unsyncedCount: Flow<Int>` — đếm PENDING/FAILED, để badge nút "Đồng bộ ngay (n)".
  - `syncNow()`:
    1. `CatalogCache.refresh()` (tiện thể làm mới giá).
    2. Lấy các đơn PENDING/FAILED (đánh SYNCING), gọi `POST /invoices/offline-sync` theo batch (vd 50 đơn/lần).
    3. Map kết quả: `SYNCED` → lưu `serverInvoiceId/serverCode`, set SYNCED; `FAILED` → lưu `errorCode/message`, `retryCount++`, để lại cho chủ xử lý/đối chiếu.
    4. Mất mạng giữa chừng → các đơn SYNCING quay lại PENDING.
  - **Idempotency an toàn**: vì khóa là `client_uuid`, đẩy lại đơn đã vào server vẫn trả SYNCED (không nhân đôi).
- **Tự đẩy khi online** (nếu chốt bật): sau `enqueue` nếu đang online → gọi `syncNow()` nền; khi app vào foreground & online → `syncNow()`.

### 4.5 POS refactor (`feature/pos/`)

- `PosRepository.search/byBarcode` → đọc **Room cache** thay vì `ProductApi` (giữ nguyên kiểu trả `ProductBriefDto`/`CartLine` để UI không đổi).
- `PosViewModel.checkout` → **luôn** `OfflineSaleRepository.enqueue(...)` rồi in bill mã tạm; KHÔNG gọi `salesApi.complete` trực tiếp nữa. (Sync tách khỏi luồng bán → bán không bao giờ chờ mạng.)
- Bỏ/ẩn ở chế độ offline: chọn khách, treo đơn, bán nợ (ngoài phạm vi). Thanh toán chỉ CASH/BANK_TRANSFER.
- Bill in (ESC/POS): thêm dòng đánh dấu **"PHIẾU TẠM — CHƯA ĐỒNG BỘ"** + mã tạm khi đơn chưa sync.

### 4.6 UI trạng thái

- **Thanh trạng thái offline/sync** ở POS (và/hoặc Hub): badge "Chưa đồng bộ: n" + nút **"Đồng bộ ngay"**; trạng thái đang sync / lỗi.
- Màn **"Đơn chưa đồng bộ"**: liệt kê outbox (mã tạm, giờ bán, tiền, trạng thái, lỗi nếu có), nút đồng bộ lại từng đơn / tất cả.
- Lỗi hiển thị bằng **ErrorDialog** dùng chung (theo memory `feedback_error_dialog`), không toast.
- Mọi text tiếng Việt (theo `feedback_vietnamese_errors`).

## 5. Các luồng chính

### 5.1 Bán offline
1. Thu ngân quét/tìm SP → đọc catalog cache → thêm giỏ.
2. Thanh toán (CASH/CK) → `enqueue` ghi Room (PENDING) + in bill mã tạm `TM-…`.
3. Giỏ clear, bán tiếp. (Không phụ thuộc mạng.)

### 5.2 Đồng bộ
1. Có mạng → bấm **"Đồng bộ ngay"** (hoặc tự đẩy nền).
2. `refresh catalog` → `POST /invoices/offline-sync` batch.
3. Server tạo HD COMPLETED, trừ tồn (cho âm), ghi sổ quỹ, trả mã thật + `caused_negative`.
4. Máy cập nhật đơn → SYNCED (lưu mã thật) / FAILED (giữ lại).
5. Chủ shop xem `/reports/offline-negative` để kiểm kho nếu có đơn làm âm.

### 5.3 Làm mới catalog
- Khi online & cache cũ → `GET /products/catalog?since=last` cập nhật giá/SP mới/xóa SP. Bán offline dùng giá tại lần cache gần nhất.

## 6. Edge cases (phải xử lý)

| Tình huống | Xử lý |
|-----------|-------|
| Đẩy lại đơn đã sync (retry/mạng chập) | `client_uuid` unique → server trả SYNCED cũ, không nhân đôi. |
| SP bị xóa/đổi giữa cache và sync | invoice_item snapshot từ máy → server lưu snapshot. Nếu `product_id` không còn → đơn `FAILED/PRODUCT_NOT_FOUND`, giữ outbox cho chủ xử lý. |
| Đổi giá online khi máy offline | Đơn dùng giá cache lúc bán (snapshot) — đó là giá bán thực, đúng. |
| Âm tồn (1 hay nhiều máy offline) | Server luôn nhận, `balance_after` âm, gắn `caused_negative`, vào `/reports/offline-negative`. |
| Một đơn trong batch lỗi | Transaction riêng từng đơn → đơn khác vẫn SYNCED; đơn lỗi giữ PENDING/FAILED. |
| Mất mạng giữa lúc sync | Đơn SYNCING → revert PENDING; lần sau đẩy lại an toàn (idempotent). |
| Lệch giờ máy | `sold_at` từ máy chỉ để hiển thị & chọn ngày sinh mã; tồn/sổ quỹ theo logic server lúc commit. |
| Chưa từng tải catalog rồi mất mạng | POS chặn bán offline + ErrorDialog "Chưa tải dữ liệu offline". Yêu cầu mở app online ít nhất 1 lần. |
| Đơn vị quy đổi (thùng/lốc) | Cache `CachedUnitEntity` + barcode đơn vị; snapshot `conversion_rate` trên item; server dùng snapshot. |
| Reprint sau sync | Sau SYNCED, đơn có `serverCode` → in lại dùng mã HD thật. |

## 7. Phân rã công việc (đề xuất thứ tự)

1. **BE-1**: Migration `invoices` (client_uuid, origin, temp_code, device_id) + unique index. Biến thể `generate_code(when=)`.
2. **BE-2**: `GET /products/catalog` (+ delta `since`) + schema + test tenant isolation.
3. **BE-3**: `POST /invoices/offline-sync` service idempotent + cho âm tồn + sổ quỹ + audit; test (idempotency, âm tồn, batch lỗi lẻ).
4. **BE-4**: `GET /reports/offline-negative` (hoặc gộp cảnh báo tồn).
5. **AND-1**: Thêm Room + entities/DAO + DI (Hilt module).
6. **AND-2**: `CatalogCache` + API `catalog` + refresh on login/POS.
7. **AND-3**: `OfflineSaleRepository.enqueue` + đổi `PosRepository.search/byBarcode/checkout` sang local-first; bill mã tạm.
8. **AND-4**: `SyncManager` + API `offline-sync` + map kết quả + `unsyncedCount`.
9. **AND-5**: UI trạng thái sync + màn "Đơn chưa đồng bộ"; ErrorDialog/i18n.
10. **AND-6**: (Tùy chọn đã chốt) tự đẩy nền khi online.

Mỗi bước có unit test (BE: pytest service; AND: DAO + ViewModel/SyncManager với fake). Test xuyên suốt: bán offline → sync → mã thật + tồn (âm) đúng + sổ quỹ đúng + idempotent khi đẩy lại.

## 8. Câu hỏi mở cần chốt khi làm UI
- `/reports/offline-negative` làm màn riêng hay gộp vào cảnh báo tồn hiện có? (chốt ở bước AND-5/BE-4)
