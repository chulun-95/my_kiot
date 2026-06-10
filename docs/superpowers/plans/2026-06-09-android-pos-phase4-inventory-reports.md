# Android POS — Phase 4: Tra cứu tồn kho + Báo cáo nhanh

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development hoặc executing-plans.

**Goal:** Tab Tồn (danh sách tồn + tìm + badge sắp hết + thẻ kho/kardex) và tab Báo cáo (dashboard hôm nay + chốt ca EOD cho OWNER). Chỉ đọc.

**Architecture:** Tiếp nối Phase 1–3. Dùng lại `InventoryApi` (inventory/low-stock/movements đã thêm ở Phase 3). Thêm `ReportApi` + DTO, `feature/inventory` và `feature/report` (Repository + ViewModel TDD nhẹ + UI). Online-only.

**Phụ thuộc backend:** `GET /inventory`, `GET /inventory/low-stock`, `GET /inventory/{product_id}/movements`, `GET /reports/dashboard`, `GET /reports/end-of-day?date=` (OWNER only).

---

## File Structure (Phase 4)
- `core/network/dto/ReportDtos.kt`; `core/network/ReportApi.kt` (+ provide Hilt)
- `feature/inventory/data/InventoryRepository.kt`, `InventoryUiState.kt`, `InventoryViewModel.kt`, `InventoryScreen.kt`, `MovementsDialog.kt`
- `feature/report/data/ReportRepository.kt`, `ReportUiState.kt`, `ReportViewModel.kt`, `ReportScreen.kt`
- `navigation/HomeScaffold`: tab Tồn → `InventoryScreen`, tab Báo cáo → `ReportScreen`
- Tests: `InventoryViewModelTest.kt`, `ReportViewModelTest.kt`

---

## Task 1: ReportApi + DTOs
- [ ] `ReportDtos.kt` (DashboardDto, EndOfDayDto, EodMethodRowDto — khớp report/schemas.py; Decimal as String).
- [ ] `ReportApi.kt`: `@GET("reports/dashboard") dashboard()`, `@GET("reports/end-of-day") endOfDay(@Query("date") date: String? = null)`.
- [ ] Provide trong `NetworkModule`.
- [ ] **Commit** `feat(android): API reports (dashboard + EOD)`.

## Task 2: Inventory feature (TDD ViewModel)
- [ ] `InventoryRepository`: `list(search, page)`, `lowStock()`, `movements(productId)` → `ApiResult`.
- [ ] **Test (fail)** `InventoryViewModelTest`: load list success → items; failure → errorMessage VN; lowStock load.
- [ ] `InventoryUiState` + `InventoryViewModel` (load on init, search, mở movements).
- [ ] Run → PASS.
- [ ] UI `InventoryScreen` (ô tìm, danh sách item: tên/SKU/tồn/min, badge "Sắp hết" nếu quantity ≤ min_stock; tap → `MovementsDialog` hiển thị kardex) + `MovementsDialog`.
- [ ] Gắn tab Tồn. **Commit** `feat(android): tra cứu tồn kho + thẻ kho`.

## Task 3: Report feature (TDD ViewModel)
- [ ] `ReportRepository`: `dashboard()`, `endOfDay(date?)` → `ApiResult`.
- [ ] **Test (fail)** `ReportViewModelTest`: dashboard success → state; failure → error VN; EOD success → state; EOD failure (403) → eod=null, KHÔNG set error (CASHIER không có quyền).
- [ ] `ReportUiState` + `ReportViewModel`.
- [ ] Run → PASS.
- [ ] UI `ReportScreen`: card doanh thu hôm nay, số đơn, KH, hàng sắp hết; mục EOD (nếu có) hiển thị closing_total + sales_revenue.
- [ ] Gắn tab Báo cáo. **Commit** `feat(android): báo cáo nhanh (dashboard + EOD)`.

## Phase 4 — Definition of Done
- Unit test xanh: `InventoryViewModelTest`, `ReportViewModelTest` (+ tất cả test các phase trước).
- App build. Thủ công: tab Tồn hiển thị tồn đúng + kardex; tab Báo cáo hiển thị doanh thu hôm nay; CASHIER không thấy EOD/giá vốn (theo backend). Lỗi tiếng Việt.

> Đây là phase cuối. Sau khi build xanh trên máy có Android SDK + smoke test 4 tab, app MVP hoàn chỉnh: Bán · Nhập · Tồn · Báo cáo.
