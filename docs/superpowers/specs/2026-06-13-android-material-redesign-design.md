# Android — Nâng cấp giao diện Material chuyên nghiệp (Nền tảng + Hub + Dashboard)

**Ngày:** 2026-06-13
**Trạng thái:** Design — chờ duyệt trước khi viết plan

## Mục tiêu

App hiện trông như bản demo/example. Nâng lên cảm giác **thương mại, chuẩn Material 3**, tham khảo KiotViet, NHƯNG giữ triết lý **đơn sắc cho chức năng/icon**, **chỉ dùng màu cho biểu đồ/dữ liệu**. Đồng thời **hợp nhất icon + màu giữa app và web** để cùng một chức năng không hiển thị khác nhau.

Phạm vi đợt này: **(1) Nền tảng hệ thiết kế · (2) Hub · (3) Dashboard (có biểu đồ màu)**. Các màn khác áp dụng dần sau bằng cùng bộ component.

## Nguyên tắc thiết kế

1. **Monochrome-first, color-for-data:** nền tảng đen/trắng/xám (thang slate); màu chỉ xuất hiện trong biểu đồ.
2. **Một nguồn chân lý:** bảng màu + bảng icon dùng chung app↔web (web là gốc tham chiếu vì đã có recharts + palette slate).
3. **Material 3 đúng chuẩn:** spacing/shape/elevation/typography nhất quán, có chiều sâu & trạng thái nhấn — không "phẳng chết".
4. **Role-aware:** biểu đồ dùng dữ liệu OWNER-only (các endpoint report bị chặn OWNER ở backend) → CASHIER thấy KPI rút gọn.

---

## 1. Color tokens — hợp nhất app ↔ web

Web hiện dùng `slate-900 #0F172A` (sidebar, stroke/fill chart) + `emerald-600 #16A34A` (lợi nhuận). App đang dùng ink `#0A0A0A` + xám **zinc** → đổi sang **slate** cho khớp.

Sửa `core/ui/theme/Color.kt`:

| Token hiện tại | Giá trị mới | Vai trò |
|---|---|---|
| `Ink` `#0A0A0A` | **`#0F172A`** slate-900 | chữ chính, primary, series chart chính |
| `InkSoft` `#6B7280` | **`#64748B`** slate-500 | chữ phụ, icon mờ |
| `Paper` `#FFFFFF` | giữ | surface |
| `PaperGray` `#F4F4F5` | **`#F8FAFC`** slate-50 | nền app |
| `PaperGrayDark` `#E9E9EB` | **`#F1F5F9`** slate-100 | fill nhẹ/chip |
| `Line` `#E4E4E7` | **`#E2E8F0`** slate-200 | viền/divider |
| `LineSoft` `#F0F0F0` | **`#EEF2F6`** | viền rất nhạt |

**Bảng màu DỮ LIỆU (chỉ dùng trong chart)** — thêm vào `Color.kt`:

```kotlin
val DataInk     = Color(0xFF0F172A) // series chính (doanh thu, top SP) — khớp web
val DataProfit  = Color(0xFF16A34A) // lợi nhuận / dương — khớp web
val DataCash    = Color(0xFF16A34A) // CASH
val DataBank    = Color(0xFF0EA5E9) // BANK_TRANSFER (sky)
val DataWallet  = Color(0xFF8B5CF6) // MOMO/ví (violet)
val DataOther   = Color(0xFFF59E0B) // khác/amber
val DataWarn    = Color(0xFFF59E0B) // cảnh báo (hàng sắp hết)
```

Donut thanh toán map theo `method`: `CASH→DataCash`, `BANK_TRANSFER→DataBank`, `MOMO→DataWallet`, còn lại→`DataOther` (xoay vòng nếu nhiều hơn).

> Theme (`Theme.kt`) `MonoLight` cập nhật `primary/onSurfaceVariant/surface/outline...` theo token mới. `error` vẫn để Ink (giữ đơn sắc cho lỗi).

## 2. Icon system — app khớp web (chỉ sửa app)

App đổi từ **Material Filled** → **Material Symbols Outlined** (mảnh, khớp Feather của web). Dùng biến thể `Icons.Outlined.*` (material-icons-extended đã có sẵn trong build). Tên cột "Icon" dưới đây là tên khái niệm; tên import chính xác (vd `Icons.Outlined.Group`, `Icons.Outlined.Description`, `Icons.AutoMirrored.Outlined.ReceiptLong`) chốt ở bước plan. Cùng chức năng = cùng khái niệm icon. Bảng ánh xạ chuẩn (nguồn chân lý — dùng cho Hub & mọi màn):

| Chức năng | Icon (Material Outlined) | Web tương ứng |
|---|---|---|
| Bán hàng (POS) | `PointOfSale` | pos (giỏ hàng) |
| Nhập hàng | `ReceiptLong` | receipt |
| Tồn kho | `Inventory2` | inventory |
| Trả hàng | `AssignmentReturn` | — |
| Sản phẩm | `Sell` | product (hộp) |
| Khách hàng | `GroupOutlined` | customer (người) |
| Nhà cung cấp | `LocalShipping` | supplier (xe tải) |
| Nhóm hàng | `FolderOutlined` | category (thư mục) |
| Hóa đơn | `DescriptionOutlined` | invoice (tài liệu) |
| Doanh thu | `TrendingUp` | revenue (đường lên) |
| Top SP | `StarOutline` | topProducts (sao) |
| Tồn kho TQ | `BarChart` | stockSummary (cột) |
| Lợi nhuận | `Payments` | profit ($) |
| Điều chỉnh kho | `TuneOutlined` | adjustment (gear) |
| Nhân viên | `BadgeOutlined` | staff |
| Đổi mật khẩu | `LockOutline` | — |

Quy ước dùng icon: tint = `onSurface` (đơn sắc), `size = 22dp` ở Hub card, `20dp` ở list/KPI.

## 3. Material 3 tokens (chống cảm giác demo)

- **Spacing scale:** 4 / 8 / 12 / 16 / 24 / 32 (dp). Thêm `object Spacing` trong `core/ui`.
- **Shape:** card lớn 20dp, card nhỏ/tile 16dp, chip/pill 50%. (đã gần đúng — chuẩn hoá lại.)
- **Elevation tinh tế:** KPI tile & ChartCard dùng `shadowElevation = 1.dp` + viền `outline` mảnh (cảm giác có chiều sâu, không phẳng). Hub card: `tonalElevation`/shadow 1dp + ripple.
- **Trạng thái nhấn:** mọi card bấm được dùng `Surface(onClick=...)` để có ripple + `interactionSource` (đã có ở Hub, mở rộng KPI).
- **Typography bổ sung** (`Type.kt`): thêm `displaySmall` (số KPI lớn) — `FontWeight.Bold`, `letterSpacing = -0.5sp`, ~30sp.

## 4. Component mới (đặt ở `core/ui/`)

Mỗi component 1 file, tự chứa, không phụ thuộc feature.

### 4.1 `KpiTile.kt`
```
KpiTile(icon, label, value, modifier, accent: Color? = null, caption: String? = null)
```
- Layout: icon nhỏ (góc trên) · label (labelMedium, slate-500) · value (displaySmall, đậm) · caption tùy chọn.
- `accent` chỉ tô chữ value khi cần (vd lợi nhuận = DataProfit); mặc định đơn sắc onSurface.
- Surface bo 16dp, viền outline, shadow 1dp. Dùng trong grid 2 cột.

### 4.2 `ChartCard.kt`
```
ChartCard(title: String, legend: List<LegendItem> = emptyList(), content: @Composable () -> Unit)
```
- Khung: tiêu đề (titleMedium) + slot biểu đồ + hàng legend (chấm màu + nhãn). Surface bo 20dp, shadow 1dp.

### 4.3 `charts/ColumnChart.kt` (Canvas)
```
ColumnChart(data: List<Pair<String, Double>>, barColor: Color = DataInk, modifier)
```
- Cột dọc, nhãn trục X (ngày), baseline, animate chiều cao khi vào (`animateFloatAsState`). Giá trị lớn nhất scale 100%. Khoảng cách cột đều. Tối giản: không lưới đậm, chỉ baseline + nhãn.

### 4.4 `charts/DonutChart.kt` (Canvas)
```
DonutChart(slices: List<Slice>, modifier)   // Slice(label, value, color)
```
- `drawArc` từng phần, lỗ giữa ~62%, animate sweep. Tổng giữa hiển thị (tổng tiền / "100%"). Legend đặt ở ChartCard.

### 4.5 `charts/HBarChart.kt` (Canvas)
```
HBarChart(data: List<Pair<String, Double>>, barColor: Color = DataInk, modifier)
```
- Thanh ngang top-5, nhãn tên SP (cắt ngắn) + giá trị cuối thanh. Animate width.

> Tất cả chart nhận dữ liệu đã chuẩn hoá (Double), không tự gọi API. Format tiền dùng `formatVnd`.

## 5. Hub redesign (`navigation/HubScreen.kt`)

Giữ cấu trúc lưới gom nhóm hiện có; **polish**:
- Icon đổi sang bộ Outlined ở §2; tint onSurface.
- Card: thêm `shadowElevation = 1.dp`, ripple rõ, chevron mảnh (`ChevronRight`, tint slate-300) góc phải-dưới hoặc cạnh phải.
- Nút **BÁN HÀNG** giữ nền Ink (#0F172A) — giờ khớp web sidebar; thêm shadow nhẹ.
- Áp `Spacing` chuẩn; section header giữ `SectionHeader`.
- Cờ `ownerOnly` (đã có sẵn) — đợt này chưa lọc role (để hướng B), nhưng giữ nguyên.

## 6. Dashboard redesign (`feature/report/ReportScreen.kt`)

Bố cục mới (cuộn dọc):

1. **Lưới KPI (2 cột)** — thay list StatCard dọc bằng `KpiTile`:
   - Doanh thu (icon TrendingUp), Số hóa đơn (DescriptionOutlined), Khách hàng (GroupOutlined), Hàng sắp hết (Inventory2, caption "hết: N").
   - Lợi nhuận (Payments, accent = DataProfit) — chỉ khi `todayProfit != null` (OWNER hoặc setting bật).
2. **ChartCard "Doanh thu 7 ngày"** → `ColumnChart` (DataInk). Dữ liệu từ `/reports/revenue?group_by=day` (7 ngày gần nhất). **OWNER-only.**
3. **ChartCard "Cơ cấu thanh toán"** → `DonutChart` + legend màu. Dữ liệu từ `/reports/end-of-day` `by_method` (total_in mỗi method). **OWNER-only.**
4. **ChartCard "Top sản phẩm"** → `HBarChart` (DataInk). Dữ liệu từ `/reports/top-products`. **OWNER-only.**

**Role-aware:** ViewModel gọi các endpoint OWNER trong `runCatching`; nếu 403 (CASHIER) → bỏ qua, chỉ hiện lưới KPI. Giống cách `endOfDay()` hiện đang nuốt lỗi 403.

### Dữ liệu / API cần thêm (app side)
`ReportApi` thêm:
- `revenue(from, to, group_by="day"): RevenueDto` — series `[{period, revenue, invoices, profit}]`.
- `topProducts(from, to, limit): TopProductsDto` — items `[{product_id, product_name, quantity_sold, revenue, profit}]`.
- `endOfDay` đã có (`by_method` dùng cho donut).

DTO mới khớp backend (Decimal→Double):
```kotlin
@Serializable data class RevenuePointDto(val period: String, val revenue: Double = 0.0,
    val invoices: Int = 0, val profit: Double = 0.0)
@Serializable data class RevenueDto(@SerialName("total_revenue") val totalRevenue: Double = 0.0,
    val series: List<RevenuePointDto> = emptyList())
@Serializable data class TopProductItemDto(@SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String, val revenue: Double = 0.0,
    @SerialName("quantity_sold") val quantitySold: Double = 0.0, val profit: Double = 0.0)
@Serializable data class TopProductsDto(val items: List<TopProductItemDto> = emptyList())
```

`ReportRepository` thêm `revenueLast7Days()` (tự tính from = hôm nay − 6, to = hôm nay, group_by=day) và `topProducts(limit=5)`. `ReportViewModel`/`ReportUiState` thêm `revenue7d`, `topProducts`, `payments` (từ eod.by_method) — đều nullable, 403 → null.

## Testing

- **Unit (mockk + turbine):** `ReportViewModel` — KPI luôn có; revenue/top/payments = null khi repo trả Failure(403), có dữ liệu khi Success. Repository `revenueLast7Days` ghép khoảng ngày đúng.
- **Chart math:** test thuần hàm scale/tỉ lệ nếu tách được (vd hàm chia tỉ lệ cột, góc donut) — tách logic tính khỏi Canvas để test.
- **UI Compose:** verify thủ công trên máy (codebase không có UI test).

## Ngoài phạm vi (đợt này)

- Redesign POS / Nhập / Tồn / Khách hàng (áp component sau).
- Lọc role ẩn card Hub (hướng B).
- Đổi icon/màu phía **web** (đã chốt chỉ sửa app).
- Dark mode.
- Tương tác chart nâng cao (tooltip chạm, zoom).

## Files (dự kiến)

```
core/ui/theme/Color.kt          # MỞ RỘNG: đổi slate + thêm Data* colors
core/ui/theme/Theme.kt          # SỬA: map token mới
core/ui/theme/Type.kt           # MỞ RỘNG: displaySmall
core/ui/Spacing.kt              # MỚI: thang spacing
core/ui/KpiTile.kt              # MỚI
core/ui/ChartCard.kt            # MỚI
core/ui/charts/ColumnChart.kt   # MỚI
core/ui/charts/DonutChart.kt    # MỚI
core/ui/charts/HBarChart.kt     # MỚI
core/network/ReportApi.kt       # MỞ RỘNG: revenue, topProducts
core/network/dto/ReportDtos.kt  # MỞ RỘNG: RevenueDto, TopProductsDto
feature/report/ReportRepository.kt  # MỞ RỘNG
feature/report/ReportViewModel.kt + ReportUiState.kt  # MỞ RỘNG
feature/report/ReportScreen.kt  # VIẾT LẠI bố cục (KPI grid + 3 ChartCard)
navigation/HubScreen.kt         # SỬA: icon outline + elevation + chevron
```
