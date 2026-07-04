# Làm mới giao diện MyKiot POS (Android) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Áp phong cách POS thương mại màu **teal** lên toàn bộ app Android, giữ nguyên 100% chức năng, cấu trúc, và logic.

**Architecture:** Đổi design tokens ở tầng theme (`core/ui/theme`) để màu teal + màu trạng thái tự lan qua mọi component dùng `MaterialTheme.colorScheme`. Thêm 2 component dùng chung mới (`StatusBadge`, `ListRow`). Quét sửa các chỗ hardcode nút màu đen sang `primary`. Cuối cùng restyle từng nhóm màn dùng component/token mới. Chỉ tầng UI thay đổi — không đụng ViewModel/data/DTO/network.

**Tech Stack:** Kotlin, Jetpack Compose, Material 3, Hilt. Build: Gradle wrapper (`android/gradlew`). Unit test: JUnit (JVM, `app/src/test`).

## Global Constraints

- **Không** thêm/bớt/gộp màn hình, route, navigation, tính năng, use case.
- **Không** sửa ViewModel, data layer, DTO, network, business logic. Diff chỉ nằm ở tầng UI (`core/ui`, `feature/**/*Screen.kt`, `navigation/`).
- Mọi text hiển thị bằng **tiếng Việt**; dùng `stringResource(...)` — không hardcode chuỗi UI mới; nếu cần chuỗi mới, thêm vào `app/src/main/res/values/strings_*.xml`.
- Lỗi hiển thị bằng `ErrorDialog` (không toast/snackbar) — giữ nguyên hành vi hiện tại.
- App chỉ có **light mode** — không thêm dark mode.
- Chạy mọi lệnh gradle từ thư mục `android/`. Lệnh compile: `./gradlew :app:compileDebugKotlin`. Lệnh test: `./gradlew :app:testDebugUnitTest`.
- Commit theo convention tiếng Việt; kết thúc message bằng:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Verify chủ đạo cho task thuần trình bày = **compile pass + rà soát trực quan** (không có Compose UI test trong dự án). Chỉ TDD ở nơi có hàm thuần (Task 3).

---

### Task 1: Design tokens teal + màu trạng thái

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/ui/theme/Color.kt`

**Interfaces:**
- Produces: các `val` màu: `Brand`, `BrandDark`, `BrandSoft`, `BrandOnSoft`, `StatusOkBg/Fg`, `StatusWarnBg/Fg`, `StatusDangerBg/Fg`, `StatusMutedBg/Fg`, `StatusInfoBg/Fg` (kiểu `androidx.compose.ui.graphics.Color`).

- [ ] **Step 1: Thêm token vào cuối `Color.kt`**

Chèn vào cuối file (giữ nguyên toàn bộ token cũ `Ink`, `Paper`, `Data*`…):

```kotlin
// ---- Thương hiệu teal ----
val Brand        = Color(0xFF0D9488) // teal-600 — primary, nút chính, tab active
val BrandDark    = Color(0xFF0F766E) // teal-700 — nhấn đậm, viền nút phụ
val BrandSoft    = Color(0xFFCCFBF1) // teal-100 — nền icon tile, badge info
val BrandOnSoft  = Color(0xFF0F766E) // chữ/icon trên nền BrandSoft

// ---- Màu trạng thái ngữ nghĩa (nền nhạt + chữ đậm) ----
val StatusOkBg     = Color(0xFFDCFCE7); val StatusOkFg     = Color(0xFF15803D) // Đã thanh toán / Còn hàng
val StatusWarnBg   = Color(0xFFFEF3C7); val StatusWarnFg   = Color(0xFFB45309) // Bán nợ / Sắp hết
val StatusDangerBg = Color(0xFFFEE2E2); val StatusDangerFg = Color(0xFFB91C1C) // Đã hủy / Hết hàng
val StatusMutedBg  = Color(0xFFF1F5F9); val StatusMutedFg  = Color(0xFF475569) // Nháp / Treo
val StatusInfoBg   = BrandSoft;         val StatusInfoFg   = BrandOnSoft        // Thông tin / nhấn phụ
```

- [ ] **Step 2: Compile**

Run (từ `android/`): `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/theme/Color.kt
git commit -m "feat(ui): thêm token màu teal + màu trạng thái ngữ nghĩa

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: ColorScheme teal + error đỏ thật

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/ui/theme/Theme.kt`

**Interfaces:**
- Consumes: token từ Task 1 (`Brand`, `BrandDark`, `BrandSoft`, `StatusDangerBg`, `StatusDangerFg`).
- Produces: `MyKiotTheme` (giữ nguyên chữ ký `@Composable fun MyKiotTheme(content: @Composable () -> Unit)`).

- [ ] **Step 1: Thay bảng màu**

Trong `Theme.kt`, đổi các dòng của `MonoLight` (đổi tên biến thành `TealLight`) như sau — giữ nguyên các slot nền trung tính, chỉ đổi primary/secondary/error:

```kotlin
private val TealLight = lightColorScheme(
    primary = Brand,
    onPrimary = Paper,
    primaryContainer = BrandSoft,
    onPrimaryContainer = BrandDark,
    secondary = BrandDark,
    onSecondary = Paper,
    secondaryContainer = PaperGray,
    onSecondaryContainer = Ink,
    tertiary = Brand,
    onTertiary = Paper,
    background = Paper,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = PaperGray,
    onSurfaceVariant = InkSoft,
    surfaceContainer = Paper,
    surfaceContainerHigh = PaperGray,
    surfaceContainerHighest = PaperGrayDark,
    outline = Line,
    outlineVariant = LineSoft,
    error = StatusDangerFg,
    onError = Paper,
    errorContainer = StatusDangerBg,
    onErrorContainer = StatusDangerFg,
    scrim = Color(0x66000000),
)
```

- [ ] **Step 2: Trỏ theme tới bảng mới**

Trong `MyKiotTheme`, đổi `colorScheme = MonoLight` → `colorScheme = TealLight`.

- [ ] **Step 3: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/theme/Theme.kt
git commit -m "feat(ui): đổi ColorScheme sang teal, error dùng đỏ thật

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: StatusBadge + hàm phân loại tồn kho (TDD)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/StatusBadge.kt`
- Create: `android/app/src/test/java/com/mykiot/pos/core/ui/StockLevelTest.kt`

**Interfaces:**
- Consumes: token màu trạng thái từ Task 1.
- Produces:
  - `enum class StatusKind { Success, Warning, Danger, Neutral, Info }`
  - `@Composable fun StatusBadge(text: String, kind: StatusKind, modifier: Modifier = Modifier)`
  - `enum class StockLevel { OK, LOW, OUT }`
  - `fun stockLevel(quantity: java.math.BigDecimal, minStock: Int): StockLevel`

- [ ] **Step 1: Viết test thất bại cho `stockLevel`**

Tạo `android/app/src/test/java/com/mykiot/pos/core/ui/StockLevelTest.kt`:

```kotlin
package com.mykiot.pos.core.ui

import org.junit.Assert.assertEquals
import org.junit.Test
import java.math.BigDecimal

class StockLevelTest {
    @Test fun `so luong 0 la OUT`() =
        assertEquals(StockLevel.OUT, stockLevel(BigDecimal.ZERO, 5))

    @Test fun `so luong am la OUT`() =
        assertEquals(StockLevel.OUT, stockLevel(BigDecimal("-2"), 5))

    @Test fun `duong va nho hon hoac bang min la LOW`() {
        assertEquals(StockLevel.LOW, stockLevel(BigDecimal("5"), 5))
        assertEquals(StockLevel.LOW, stockLevel(BigDecimal("3"), 5))
    }

    @Test fun `lon hon min la OK`() =
        assertEquals(StockLevel.OK, stockLevel(BigDecimal("6"), 5))

    @Test fun `min bang 0 thi moi so duong deu OK`() =
        assertEquals(StockLevel.OK, stockLevel(BigDecimal("1"), 0))
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.ui.StockLevelTest"`
Expected: FAIL (unresolved reference `stockLevel` / `StockLevel`).

- [ ] **Step 3: Viết `StatusBadge.kt` (gồm cả `stockLevel`)**

```kotlin
package com.mykiot.pos.core.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.theme.StatusDangerBg
import com.mykiot.pos.core.ui.theme.StatusDangerFg
import com.mykiot.pos.core.ui.theme.StatusInfoBg
import com.mykiot.pos.core.ui.theme.StatusInfoFg
import com.mykiot.pos.core.ui.theme.StatusMutedBg
import com.mykiot.pos.core.ui.theme.StatusMutedFg
import com.mykiot.pos.core.ui.theme.StatusOkBg
import com.mykiot.pos.core.ui.theme.StatusOkFg
import com.mykiot.pos.core.ui.theme.StatusWarnBg
import com.mykiot.pos.core.ui.theme.StatusWarnFg
import java.math.BigDecimal

enum class StatusKind { Success, Warning, Danger, Neutral, Info }

private fun StatusKind.bg(): Color = when (this) {
    StatusKind.Success -> StatusOkBg
    StatusKind.Warning -> StatusWarnBg
    StatusKind.Danger -> StatusDangerBg
    StatusKind.Neutral -> StatusMutedBg
    StatusKind.Info -> StatusInfoBg
}

private fun StatusKind.fg(): Color = when (this) {
    StatusKind.Success -> StatusOkFg
    StatusKind.Warning -> StatusWarnFg
    StatusKind.Danger -> StatusDangerFg
    StatusKind.Neutral -> StatusMutedFg
    StatusKind.Info -> StatusInfoFg
}

/** Nhãn trạng thái dạng pill: nền nhạt + chữ đậm theo ngữ nghĩa. */
@Composable
fun StatusBadge(text: String, kind: StatusKind, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(kind.bg(), RoundedCornerShape(50))
            .padding(horizontal = 10.dp, vertical = 3.dp),
    ) {
        Text(
            text,
            style = MaterialTheme.typography.labelMedium,
            color = kind.fg(),
            fontWeight = FontWeight.SemiBold,
        )
    }
}

enum class StockLevel { OK, LOW, OUT }

/** Phân loại tồn: <=0 OUT; >0 và <=min LOW; còn lại OK. min=0 ⇒ mọi số dương là OK. */
fun stockLevel(quantity: BigDecimal, minStock: Int): StockLevel = when {
    quantity.signum() <= 0 -> StockLevel.OUT
    quantity <= BigDecimal(minStock) -> StockLevel.LOW
    else -> StockLevel.OK
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.ui.StockLevelTest"`
Expected: PASS (5 test).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/StatusBadge.kt android/app/src/test/java/com/mykiot/pos/core/ui/StockLevelTest.kt
git commit -m "feat(ui): StatusBadge + hàm thuần stockLevel (có test)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Component ListRow (danh sách gạch phân cách)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/ListRow.kt`

**Interfaces:**
- Produces:
  ```kotlin
  @Composable fun ListRow(
      title: String,
      modifier: Modifier = Modifier,
      subtitle: String? = null,
      leading: @Composable (() -> Unit)? = null,
      trailing: @Composable (() -> Unit)? = null,
      onClick: (() -> Unit)? = null,
      showDivider: Boolean = true,
  )
  ```

- [ ] **Step 1: Tạo `ListRow.kt`**

```kotlin
package com.mykiot.pos.core.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/**
 * Hàng danh sách chuẩn (kiểu gạch phân cách): leading tùy chọn (emoji/thumbnail),
 * tiêu đề + phụ đề, trailing tùy chọn (giá + StatusBadge). Divider mảnh phía dưới.
 * Dùng chung cho Sản phẩm / Tồn kho / Hóa đơn / Phiếu nhập / Khách hàng / NCC.
 */
@Composable
fun ListRow(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    leading: @Composable (() -> Unit)? = null,
    trailing: @Composable (() -> Unit)? = null,
    onClick: (() -> Unit)? = null,
    showDivider: Boolean = true,
) {
    Column(modifier.fillMaxWidth()) {
        Row(
            Modifier
                .fillMaxWidth()
                .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
                .heightIn(min = 64.dp)
                .padding(vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leading != null) {
                leading()
                Spacer(Modifier.width(12.dp))
            }
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.SemiBold, maxLines = 1)
                if (subtitle != null) {
                    Spacer(Modifier.height(2.dp))
                    Text(
                        subtitle,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                    )
                }
            }
            if (trailing != null) {
                Spacer(Modifier.width(12.dp))
                trailing()
            }
        }
        if (showDivider) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    }
}
```

> Ghi chú: `Spacer(Modifier.height(2.dp))` cần import `androidx.compose.foundation.layout.height` — thêm import nếu IDE báo thiếu.

- [ ] **Step 2: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/ListRow.kt
git commit -m "feat(ui): component ListRow kiểu gạch phân cách dùng chung

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Quét đổi nút/FAB màu đen sang teal (primary)

Mục tiêu: không còn nút chính/FAB nào hardcode `containerColor = MaterialTheme.colorScheme.onSurface` (đen). Đổi cặp container/content sang `primary`/`onPrimary` để dùng teal.

**Files (modify):**
- `feature/product/ProductListScreen.kt`
- `feature/product/AddProductScreen.kt`
- `feature/supplier/SupplierListScreen.kt`
- `feature/supplier/AddSupplierScreen.kt`
- `feature/customer/CustomerListScreen.kt`
- `feature/customer/AddCustomerScreen.kt`
- `feature/receipt/GoodsReceiptDetailScreen.kt`
- `feature/receipt/ReceiptScreen.kt`
- `feature/invoice/ReturnFormScreen.kt`
- `feature/account/ChangePasswordScreen.kt`
- `feature/auth/LoginScreen.kt`
- `feature/pos/PosScreen.kt`

(đường dẫn đầy đủ có tiền tố `android/app/src/main/java/com/mykiot/pos/`)

- [ ] **Step 1: Tìm mọi vị trí cần đổi**

Run (từ `android/`):
`grep -rn "colorScheme.onSurface" app/src/main/java/com/mykiot/pos/feature | grep -i "containerColor\|contentColor"`
Ghi lại danh sách dòng.

- [ ] **Step 2: Đổi từng cặp**

Trong mỗi vị trí là **nút chính hoặc FAB** (Button/FloatingActionButton), đổi:
- `containerColor = MaterialTheme.colorScheme.onSurface` → `containerColor = MaterialTheme.colorScheme.primary`
- `contentColor = MaterialTheme.colorScheme.surface` → `contentColor = MaterialTheme.colorScheme.onPrimary`

Với **nút phụ OutlinedButton** đang viền `BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface)` (ví dụ nút "Treo đơn" trong `PosScreen.kt`), đổi viền sang `MaterialTheme.colorScheme.primary` và thêm/để `contentColor` mặc định (teal) — nếu OutlinedButton chưa set content color, thêm:
`colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.primary)`.

> KHÔNG đổi các `onSurface` dùng cho **chữ/icon/cursor/viền input** (không phải nút chính) — chỉ đổi container/content của Button/FAB và viền nút phụ chính.

- [ ] **Step 3: Xác nhận không còn nút đen**

Run: `grep -rn "containerColor = MaterialTheme.colorScheme.onSurface" app/src/main/java/com/mykiot/pos/feature`
Expected: không còn kết quả nào là nút chính (rỗng, hoặc chỉ còn chỗ cố ý không phải nút — ghi rõ nếu có).

- [ ] **Step 4: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature
git commit -m "style(ui): nút chính/FAB dùng màu teal thay vì đen

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Hub — icon tile teal nhạt (soft)

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt`

**Interfaces:**
- Consumes: token `BrandSoft`, `BrandOnSoft` (Task 1).

- [ ] **Step 1: Đổi `PosButton` sang teal rõ**

`PosButton` đang dùng `color = MaterialTheme.colorScheme.primary` → sau Task 2 đã tự thành teal. Giữ nguyên; chỉ tăng nhấn: đổi `shadowElevation = 2.dp` → `shadowElevation = 4.dp`.

- [ ] **Step 2: Đổi ô icon của `HubCard` sang tile teal nhạt**

Trong `HubCard`, bọc icon module bằng một ô nền teal nhạt. Thay khối `Icon(item.icon, …, tint = onSurface, modifier = size(30.dp))` bằng:

```kotlin
Box(
    Modifier
        .size(44.dp)
        .background(com.mykiot.pos.core.ui.theme.BrandSoft, RoundedCornerShape(12.dp)),
    contentAlignment = Alignment.Center,
) {
    Icon(
        item.icon,
        contentDescription = null,
        tint = com.mykiot.pos.core.ui.theme.BrandOnSoft,
        modifier = Modifier.size(24.dp),
    )
}
```

Thêm import nếu thiếu: `androidx.compose.foundation.background`, `androidx.compose.foundation.layout.Box`, `androidx.compose.foundation.layout.size`, `androidx.compose.foundation.shape.RoundedCornerShape`, `androidx.compose.ui.Alignment`.

- [ ] **Step 3: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Rà soát trực quan**

Chạy app (hoặc preview), mở Hub: mỗi thẻ module có ô icon nền teal nhạt, nút Bán hàng teal nổi bật. Nội dung/nhóm không đổi.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt
git commit -m "style(hub): icon tile nền teal nhạt, nút bán hàng nổi bật hơn

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: POS — áp phong cách đã duyệt

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/pos/PosScreen.kt`

**Interfaces:**
- Consumes: token teal (Task 1), Task 5 đã đổi nút Thanh toán/Quét sang primary.

- [ ] **Step 1: Nút quét mã dạng tròn teal**

`trailing` của `AppSearchField` (IconButton chứa `Icons.Filled.QrCodeScanner`) — bọc icon trong nền tròn teal:

```kotlin
trailing = {
    IconButton(onClick = { scanMode = true }) {
        Box(
            Modifier
                .size(36.dp)
                .background(MaterialTheme.colorScheme.primary, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Filled.QrCodeScanner,
                contentDescription = stringResource(R.string.pos_scan_barcode),
                tint = MaterialTheme.colorScheme.onPrimary,
            )
        }
    }
},
```

Thêm import: `androidx.compose.foundation.background`, `androidx.compose.foundation.shape.CircleShape`, `androidx.compose.foundation.layout.size`.

- [ ] **Step 2: Badge "đơn treo" teal nhạt**

TextButton hiển thị `pos_held_orders_count` — thay bằng `StatusBadge(text = ..., kind = StatusKind.Info)` bọc trong `TextButton`/`clickable` để vẫn mở drafts:

```kotlin
if (state.drafts.isNotEmpty()) {
    Box(Modifier.clickable { viewModel.openDrafts() }) {
        StatusBadge(
            text = stringResource(R.string.pos_held_orders_count, state.drafts.size),
            kind = StatusKind.Info,
        )
    }
}
```

Thêm import: `com.mykiot.pos.core.ui.StatusBadge`, `com.mykiot.pos.core.ui.StatusKind`, `androidx.compose.foundation.clickable`, `androidx.compose.foundation.layout.Box`.

- [ ] **Step 3: Nút Thanh toán/Treo đơn**

Sau Task 5, nút "Thanh toán" đã dùng `primary`/`onPrimary` (teal) và "Treo đơn" viền teal. Thêm bóng cho nút Thanh toán: nếu `Button` chưa có, thêm `elevation = ButtonDefaults.buttonElevation(defaultElevation = 3.dp)`. Import `androidx.compose.material3.ButtonDefaults` nếu thiếu.

- [ ] **Step 4: Compile + rà soát trực quan**

Run: `./gradlew :app:compileDebugKotlin` → BUILD SUCCESSFUL.
Mở POS: nút quét tròn teal, badge đơn treo teal nhạt, nút Thanh toán teal có bóng, Treo đơn viền teal. Luồng bán hàng không đổi.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/pos/PosScreen.kt
git commit -m "style(pos): nút quét tròn teal, badge đơn treo, nút thanh toán nổi bật

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Tồn kho — ListRow + StatusBadge tồn kho

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/inventory/InventoryScreen.kt`

**Interfaces:**
- Consumes: `ListRow` (Task 4), `StatusBadge`, `StatusKind`, `stockLevel`, `StockLevel` (Task 3).

- [ ] **Step 1: Viết lại `InventoryItemRow` dùng ListRow + stockLevel**

Thay toàn bộ `InventoryItemRow` (dòng ~163–203) bằng:

```kotlin
@Composable
private fun InventoryItemRow(item: InventoryItemDto, onClick: () -> Unit) {
    val qty = item.quantity.toBigDecimalOrZero()
    val level = stockLevel(qty, item.minStock)
    ListRow(
        title = item.productName,
        subtitle = stringResource(R.string.inv_sku_unit, item.productSku, item.unit),
        onClick = onClick,
        trailing = {
            Column(horizontalAlignment = Alignment.End) {
                Text(formatQty(qty), style = MaterialTheme.typography.titleMedium)
                when (level) {
                    StockLevel.OUT -> {
                        Spacer(Modifier.height(4.dp))
                        StatusBadge(stringResource(R.string.inv_badge_out), StatusKind.Danger)
                    }
                    StockLevel.LOW -> {
                        Spacer(Modifier.height(4.dp))
                        StatusBadge(stringResource(R.string.inv_badge_low), StatusKind.Warning)
                    }
                    StockLevel.OK -> Unit
                }
            }
        },
    )
}
```

- [ ] **Step 2: Dọn import**

Xóa import không dùng nữa: `MonoBadge`, `Card`, `CardDefaults`, `BorderStroke`, `RoundedCornerShape`, `clickable` (nếu không còn dùng chỗ khác trong file), `heightIn`. Thêm: `com.mykiot.pos.core.ui.ListRow`, `com.mykiot.pos.core.ui.StatusBadge`, `com.mykiot.pos.core.ui.StatusKind`, `com.mykiot.pos.core.ui.StockLevel`, `com.mykiot.pos.core.ui.stockLevel`.

- [ ] **Step 3: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL (sửa import còn thiếu/thừa nếu báo lỗi).

- [ ] **Step 4: Rà soát trực quan**

Tồn kho tab "Tất cả" và "Sắp hết": hàng dạng gạch phân cách, badge Hết hàng (đỏ) / Sắp hết (vàng), còn hàng không badge.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/inventory/InventoryScreen.kt
git commit -m "style(inventory): ListRow + StatusBadge tồn kho (đỏ/vàng)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Sản phẩm — ListRow + badge INACTIVE

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/ProductListScreen.kt`

**Interfaces:**
- Consumes: `ListRow` (Task 4), `StatusBadge`/`StatusKind` (Task 3).

- [ ] **Step 1: Viết lại `ProductListCard` dùng ListRow**

Thay `ProductListCard` (dòng ~118–163) bằng:

```kotlin
@Composable
private fun ProductListCard(product: ProductBriefDto, onClick: () -> Unit) {
    ListRow(
        title = product.name,
        subtitle = stringResource(
            R.string.cat_product_list_subtitle, product.sku, product.unit, formatVnd(product.salePrice.toLong()),
        ),
        onClick = onClick,
        trailing = {
            if (product.status == "INACTIVE") {
                StatusBadge(stringResource(R.string.cat_product_status_inactive_short), StatusKind.Neutral)
            } else {
                Icon(
                    Icons.Outlined.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.outline,
                )
            }
        },
    )
}
```

- [ ] **Step 2: Dọn import**

Xóa: `MonoBadge`, `Card`, `CardDefaults`, `BorderStroke`, `heightIn`, `width` (nếu không còn dùng). Thêm: `com.mykiot.pos.core.ui.ListRow`, `com.mykiot.pos.core.ui.StatusBadge`, `com.mykiot.pos.core.ui.StatusKind`.

- [ ] **Step 3: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Rà soát trực quan**

Danh sách SP dạng gạch phân cách; SP ngừng bán có badge xám "Ngừng bán"; SP thường có mũi tên ›.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/product/ProductListScreen.kt
git commit -m "style(product): danh sách ListRow + badge trạng thái INACTIVE

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Hóa đơn — ListRow + StatusBadge trạng thái

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListScreen.kt`

**Interfaces:**
- Consumes: `ListRow`, `StatusBadge`, `StatusKind`.

- [ ] **Step 1: Đổi badge trạng thái trong `InvoiceCard`**

Trong `InvoiceCard`, thay `MonoBadge(...)` (dòng ~143–147) bằng:

```kotlin
StatusBadge(
    text = if (invoice.status == "COMPLETED") stringResource(R.string.misc_invoice_status_sold)
    else stringResource(R.string.misc_invoice_status_cancelled),
    kind = if (invoice.status == "COMPLETED") StatusKind.Success else StatusKind.Danger,
)
```

> Giữ nguyên cấu trúc `Card` của `InvoiceCard` (hóa đơn hiển thị nhiều dòng: mã, khách, ngày, tổng, nút hủy — không hợp `ListRow` 1 dòng). Chỉ đổi badge + đảm bảo màu nút hủy dùng `error` (đã là đỏ sau Task 2).

- [ ] **Step 2: Dọn import**

Xóa `MonoBadge`; thêm `com.mykiot.pos.core.ui.StatusBadge`, `com.mykiot.pos.core.ui.StatusKind`.

- [ ] **Step 3: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Rà soát trực quan**

Lịch sử hóa đơn: badge "Đã bán" (xanh lá) / "Đã hủy" (đỏ); nút "Hủy" chữ đỏ.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListScreen.kt
git commit -m "style(invoice): StatusBadge trạng thái đã bán/đã hủy

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Phiếu nhập — StatusBadge + đồng bộ màu

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/receipt/GoodsReceiptListScreen.kt`

**Interfaces:**
- Consumes: `StatusBadge`, `StatusKind`.

- [ ] **Step 1: Xác định badge hiện có**

Run: `grep -n "MonoBadge" app/src/main/java/com/mykiot/pos/feature/receipt/GoodsReceiptListScreen.kt`
Với mỗi `MonoBadge` biểu thị trạng thái phiếu, thay bằng `StatusBadge` với `kind`:
- Hoàn tất/COMPLETED → `StatusKind.Success`
- Nháp/DRAFT → `StatusKind.Neutral`
- Đã hủy/CANCELLED (nếu có) → `StatusKind.Danger`

Giữ nguyên text (`stringResource(...)`) đang dùng.

- [ ] **Step 2: Dọn import**

Xóa `MonoBadge` nếu không còn dùng; thêm `com.mykiot.pos.core.ui.StatusBadge`, `com.mykiot.pos.core.ui.StatusKind`.

- [ ] **Step 3: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Rà soát trực quan**

Lịch sử phiếu nhập: badge trạng thái đúng màu ngữ nghĩa.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/receipt/GoodsReceiptListScreen.kt
git commit -m "style(receipt): StatusBadge trạng thái phiếu nhập

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Báo cáo — accent teal cho KPI & chart

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/report/ReportScreen.kt`

**Interfaces:**
- Consumes: token `Brand` (Task 1). `KpiTile(accent = ...)`, `ChartCard` giữ nguyên chữ ký.

- [ ] **Step 1: Đặt accent teal cho KPI chính**

Run: `grep -n "KpiTile\|DataInk\|accent" app/src/main/java/com/mykiot/pos/feature/report/ReportScreen.kt`
Với các `KpiTile` doanh thu/tổng quan đang không set `accent` hoặc set màu đen, truyền `accent = com.mykiot.pos.core.ui.theme.Brand`. Giữ `DataProfit` (xanh lá) cho KPI lợi nhuận, `DataWarn` cho cảnh báo — không đổi ý nghĩa màu dữ liệu.

- [ ] **Step 2: Series chính của chart về teal (tùy chọn, nếu đang dùng `DataInk`)**

Nếu chart doanh thu dùng `DataInk` cho series chính, đổi sang `Brand` để đồng bộ thương hiệu. Legend `LegendItem` cập nhật màu tương ứng. KHÔNG đổi các series phân loại thanh toán (`DataCash/DataBank/DataWallet`).

- [ ] **Step 3: Compile**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Rà soát trực quan**

Báo cáo: số KPI chính màu teal; chart doanh thu series teal; màu lợi nhuận/cảnh báo giữ nguyên.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/report/ReportScreen.kt
git commit -m "style(report): accent teal cho KPI và series chart chính

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Khách hàng & Nhà cung cấp — ListRow

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListScreen.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/supplier/SupplierListScreen.kt`

**Interfaces:**
- Consumes: `ListRow` (Task 4).

- [ ] **Step 1: Xem cấu trúc item hiện tại**

Run: `grep -n "private fun .*Card\|Card(" app/src/main/java/com/mykiot/pos/feature/customer/CustomerListScreen.kt app/src/main/java/com/mykiot/pos/feature/supplier/SupplierListScreen.kt`

- [ ] **Step 2: Chuyển item card → ListRow (Khách hàng)**

Thay composable render 1 khách hàng (Card + Row) bằng `ListRow(title = <tên>, subtitle = <sđt / tổng chi tiêu như đang hiển thị>, onClick = ..., trailing = { Icon(Icons.Outlined.ChevronRight, null, tint = MaterialTheme.colorScheme.outline) })`. Giữ đúng các trường đang hiển thị, không thêm dữ liệu mới.

- [ ] **Step 3: Chuyển item card → ListRow (NCC)**

Tương tự cho `SupplierListScreen.kt`.

- [ ] **Step 4: Dọn import + Compile**

Xóa `Card/CardDefaults/BorderStroke` nếu không còn dùng; thêm `com.mykiot.pos.core.ui.ListRow`.
Run: `./gradlew :app:compileDebugKotlin` → BUILD SUCCESSFUL.

- [ ] **Step 5: Rà soát trực quan + Commit**

Danh sách KH/NCC dạng gạch phân cách, mũi tên ›.

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListScreen.kt android/app/src/main/java/com/mykiot/pos/feature/supplier/SupplierListScreen.kt
git commit -m "style(customer,supplier): danh sách dùng ListRow gạch phân cách

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Rà soát cuối — build đầy đủ + kiểm thử trực quan toàn app

**Files:** (không sửa mới trừ khi phát hiện sót)

- [ ] **Step 1: Build debug đầy đủ**

Run: `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 2: Chạy toàn bộ unit test**

Run: `./gradlew :app:testDebugUnitTest`
Expected: PASS toàn bộ (gồm `StockLevelTest`).

- [ ] **Step 3: Rà soát màu đơn sắc còn sót**

Run: `grep -rn "colorScheme.onSurface" app/src/main/java/com/mykiot/pos/feature | grep -i "containerColor"`
Expected: rỗng. Nếu còn, xử lý như Task 5.

- [ ] **Step 4: Checklist trực quan theo nhóm màn**

Cài APK debug, đi qua: Đăng nhập → Hub → POS (bán 1 đơn) → Sản phẩm/Tồn kho → Hóa đơn → Phiếu nhập → Khách hàng/NCC → Báo cáo → Đổi mật khẩu. Xác nhận:
- Nút chính teal, không còn nút đen.
- Badge trạng thái đúng màu ngữ nghĩa.
- Danh sách dạng gạch phân cách.
- Không có màn nào lỗi hiển thị / crash. Chức năng hoạt động như trước.

- [ ] **Step 5: Commit (nếu có sửa sót) + kết thúc**

```bash
git add -A
git commit -m "style(ui): rà soát cuối, đồng bộ màu teal toàn app

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (đã thực hiện khi viết plan)

- **Spec coverage:** tokens (T1–2), StatusBadge+màu trạng thái (T3), ListRow (T4), nút teal (T5), Hub (T6), POS (T7), Tồn kho (T8), Sản phẩm (T9), Hóa đơn (T10), Phiếu nhập (T11), Báo cáo (T12), KH/NCC (T13), rà soát cuối + form/login/change-password/detail phủ qua T5+T14. Các màn detail/form nhỏ (AddProduct, AddCustomer, AddSupplier, ChangePassword, Login, ReturnForm, ReceiptScreen, GoodsReceiptDetail, ProductDetail, CustomerDetail, CategoryTree) được phủ màu chính qua Task 5 (nút teal) + theme tự lan (field focus, tab) từ Task 2 — không cần task riêng vì không có badge/list cần đổi.
- **Placeholder scan:** không có TBD/TODO; mọi step có lệnh/đoạn code cụ thể.
- **Type consistency:** `StatusKind`, `StockLevel`, `stockLevel(BigDecimal, Int)`, `StatusBadge(text, kind, modifier)`, `ListRow(title, modifier, subtitle, leading, trailing, onClick, showDivider)` dùng nhất quán ở mọi task tiêu thụ.
