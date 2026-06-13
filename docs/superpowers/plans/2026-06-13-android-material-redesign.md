# Android — Nâng cấp giao diện Material (Nền tảng + Hub + Dashboard) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng giao diện app từ "demo" lên cảm giác thương mại chuẩn Material 3 — đơn sắc (thang slate, hợp nhất với web) cho chức năng/icon, màu chỉ dùng cho biểu đồ; dựng lưới KPI + 3 biểu đồ Canvas trên Dashboard và polish Hub.

**Architecture:** Giữ kiến trúc hiện có (Hilt, Retrofit + kotlinx.serialization, repository `open` + `ApiResult`, HiltViewModel + `StateFlow`). Tách logic tính biểu đồ thành hàm thuần (test được); biểu đồ vẽ bằng Compose Canvas, không thêm thư viện. Dashboard role-aware: gọi endpoint OWNER-only trong `runCatching`, 403 → bỏ qua.

**Tech Stack:** Kotlin, Jetpack Compose Material3, Compose Canvas, Hilt, Retrofit, kotlinx.serialization, JUnit4 + mockk + kotlinx-coroutines-test.

**Spec:** `docs/superpowers/specs/2026-06-13-android-material-redesign-design.md`

---

## Ghi chú build (môi trường hiện tại)

Repo thiếu `gradlew`/`gradlew.bat`. Dùng bản gradle đã cache. Đặt biến một lần mỗi shell (Git Bash):

```bash
export JAVA_HOME="/c/Program Files/Java/jdk-17"
GRADLE="/c/Users/VuongNV/.gradle/wrapper/dists/gradle-8.11.1-bin/bpt9gzteqjrbo1mjrsomdt32c/gradle-8.11.1/bin/gradle"
```

- Biên dịch: `"$GRADLE" :app:compileDebugKotlin --console=plain`
- Test: `"$GRADLE" :app:testDebugUnitTest --tests "<pattern>" --console=plain`
- Mọi lệnh chạy từ thư mục `android/`.

---

## File Structure

```
core/ui/theme/Color.kt        # MỞ RỘNG: slate tokens + Data* colors
core/ui/theme/Theme.kt        # SỬA: map MonoLight theo token mới
core/ui/theme/Type.kt         # MỞ RỘNG: displaySmall
core/ui/Spacing.kt            # MỚI: thang spacing
core/ui/KpiTile.kt            # MỚI: ô KPI (icon + label + số lớn)
core/ui/ChartCard.kt          # MỚI: khung biểu đồ + legend
core/ui/charts/ChartMath.kt   # MỚI: hàm thuần (normalize, sweepAngles) — TEST
core/ui/charts/ColumnChart.kt # MỚI: Canvas cột dọc
core/ui/charts/DonutChart.kt  # MỚI: Canvas donut
core/ui/charts/HBarChart.kt   # MỚI: Canvas thanh ngang
core/util/DateRanges.kt       # MỚI: last7DaysRange — TEST
core/network/dto/ReportDtos.kt# MỞ RỘNG: RevenueDto, TopProductsDto
core/network/ReportApi.kt     # MỞ RỘNG: revenue, topProducts
feature/report/data/ReportRepository.kt  # MỞ RỘNG: revenueLast7Days, topProducts
feature/report/ReportUiState.kt          # MỞ RỘNG: revenue7d, topProducts, payments
feature/report/ReportViewModel.kt        # MỞ RỘNG: load role-aware — TEST
feature/report/ReportScreen.kt           # VIẾT LẠI: KPI grid + 3 ChartCard
navigation/HubScreen.kt                   # SỬA: icon Outlined + elevation + chevron
```

---

## PHASE A — Design tokens

### Task A1: Color.kt — slate + màu dữ liệu

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/ui/theme/Color.kt`

- [ ] **Step 1: Thay nội dung Color.kt**

```kotlin
package com.mykiot.pos.core.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * Bảng màu ĐƠN SẮC theo thang slate (đồng nhất với web slate-900/slate-50).
 * Điểm nhấn dùng độ đậm/fill. MÀU chỉ xuất hiện trong biểu đồ (Data* bên dưới).
 */
val Ink = Color(0xFF0F172A)          // slate-900 — chữ chính, primary, series chart chính
val InkSoft = Color(0xFF64748B)      // slate-500 — chữ phụ, icon mờ
val Paper = Color(0xFFFFFFFF)        // surface
val PaperGray = Color(0xFFF8FAFC)    // slate-50 — nền app
val PaperGrayDark = Color(0xFFF1F5F9)// slate-100 — fill nhẹ/chip
val Line = Color(0xFFE2E8F0)         // slate-200 — viền/divider
val LineSoft = Color(0xFFEEF2F6)     // viền rất nhạt

// ---- Màu DỮ LIỆU: chỉ dùng trong biểu đồ ----
val DataInk = Color(0xFF0F172A)      // series chính (doanh thu, top SP) — khớp web #0f172a
val DataProfit = Color(0xFF16A34A)   // lợi nhuận / dương — khớp web #16a34a
val DataCash = Color(0xFF16A34A)     // CASH
val DataBank = Color(0xFF0EA5E9)     // BANK_TRANSFER (sky)
val DataWallet = Color(0xFF8B5CF6)   // MOMO / ví (violet)
val DataOther = Color(0xFFF59E0B)    // khác (amber)
val DataWarn = Color(0xFFF59E0B)     // cảnh báo (hàng sắp hết)
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/theme/Color.kt
git commit -m "feat(android): color tokens slate + bảng màu dữ liệu cho chart"
```

### Task A2: Theme.kt — map token (đã tự động qua biến)

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/ui/theme/Theme.kt`

`MonoLight` đã tham chiếu các biến `Ink/InkSoft/Paper/PaperGray/PaperGrayDark/Line/LineSoft` nên đổi giá trị ở A1 là đủ. Task này chỉ xác nhận không cần sửa thêm.

- [ ] **Step 1: Mở `Theme.kt`, xác nhận `MonoLight` chỉ dùng các biến trên (không hardcode hex). Không sửa gì.**

- [ ] **Step 2: Biên dịch để chắc chắn**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL. (Không có commit nếu không đổi file.)

### Task A3: Type.kt — thêm displaySmall

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/ui/theme/Type.kt`

- [ ] **Step 1: Thêm `displaySmall` vào `MonoTypography`**

Trong khối `MonoTypography = Typography(`, thêm property (sau `headlineSmall`):

```kotlin
    displaySmall = base.displaySmall.copy(
        fontWeight = FontWeight.Bold,
        letterSpacing = (-0.5).sp,
        fontSize = 30.sp,
        lineHeight = 36.sp,
    ),
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/theme/Type.kt
git commit -m "feat(android): typography displaySmall cho số KPI"
```

### Task A4: Spacing.kt — thang spacing

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/Spacing.kt`

- [ ] **Step 1: Tạo Spacing**

```kotlin
package com.mykiot.pos.core.ui

import androidx.compose.ui.unit.dp

/** Thang spacing chuẩn — dùng thay cho số dp rải rác. */
object Spacing {
    val xs = 4.dp
    val sm = 8.dp
    val md = 12.dp
    val lg = 16.dp
    val xl = 24.dp
    val xxl = 32.dp
}
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/Spacing.kt
git commit -m "feat(android): thang Spacing chuẩn"
```

---

## PHASE B — Component & biểu đồ

### Task B1: ChartMath.kt — hàm thuần (TDD)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/charts/ChartMath.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/core/ui/charts/ChartMathTest.kt`

- [ ] **Step 1: Viết test thất bại**

```kotlin
package com.mykiot.pos.core.ui.charts

import org.junit.Assert.assertEquals
import org.junit.Test

class ChartMathTest {
    @Test fun `normalize divides by max`() {
        val r = ChartMath.normalize(listOf(0.0, 5.0, 10.0))
        assertEquals(0.0f, r[0], 0.0001f)
        assertEquals(0.5f, r[1], 0.0001f)
        assertEquals(1.0f, r[2], 0.0001f)
    }

    @Test fun `normalize all zero when max is zero`() {
        val r = ChartMath.normalize(listOf(0.0, 0.0))
        assertEquals(0.0f, r[0], 0.0001f)
        assertEquals(0.0f, r[1], 0.0001f)
    }

    @Test fun `sweepAngles split 360 by share`() {
        val r = ChartMath.sweepAngles(listOf(1.0, 3.0))
        assertEquals(90.0f, r[0], 0.0001f)
        assertEquals(270.0f, r[1], 0.0001f)
    }

    @Test fun `sweepAngles all zero when total is zero`() {
        val r = ChartMath.sweepAngles(listOf(0.0, 0.0))
        assertEquals(0.0f, r[0], 0.0001f)
    }
}
```

- [ ] **Step 2: Chạy → FAIL**

Run: `"$GRADLE" :app:testDebugUnitTest --tests "*ChartMathTest*" --console=plain`
Expected: FAIL — `ChartMath` chưa tồn tại.

- [ ] **Step 3: Viết ChartMath**

```kotlin
package com.mykiot.pos.core.ui.charts

/** Hàm thuần tính tỉ lệ cho biểu đồ — tách khỏi Canvas để test. */
object ChartMath {
    /** Mỗi giá trị / max → [0f,1f]. max<=0 → tất cả 0f. */
    fun normalize(values: List<Double>): List<Float> {
        val max = values.maxOrNull() ?: 0.0
        if (max <= 0.0) return values.map { 0f }
        return values.map { (it / max).toFloat() }
    }

    /** Chia 360° theo tỉ trọng. total<=0 → tất cả 0f. */
    fun sweepAngles(values: List<Double>): List<Float> {
        val total = values.sum()
        if (total <= 0.0) return values.map { 0f }
        return values.map { (it / total * 360.0).toFloat() }
    }
}
```

- [ ] **Step 4: Chạy → PASS**

Run: `"$GRADLE" :app:testDebugUnitTest --tests "*ChartMathTest*" --console=plain`
Expected: PASS (4 test).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/charts/ChartMath.kt \
        android/app/src/test/java/com/mykiot/pos/core/ui/charts/ChartMathTest.kt
git commit -m "feat(android): ChartMath (normalize, sweepAngles) + test"
```

### Task B2: KpiTile.kt

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/KpiTile.kt`

- [ ] **Step 1: Tạo KpiTile**

```kotlin
package com.mykiot.pos.core.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight

/** Ô KPI: icon nhỏ + nhãn + số lớn (+ caption tùy chọn). Dùng trong lưới 2 cột. */
@Composable
fun KpiTile(
    icon: ImageVector,
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    accent: Color? = null,
    caption: String? = null,
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        shadowElevation = 1.dp,
        modifier = modifier.height(112.dp),
    ) {
        Column(Modifier.padding(14.dp)) {
            Icon(
                icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                value,
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Bold,
                color = accent ?: MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
            )
            caption?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
```

> Cần import `androidx.compose.ui.unit.dp`. Thêm dòng `import androidx.compose.ui.unit.dp` ở đầu file.

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/KpiTile.kt
git commit -m "feat(android): component KpiTile"
```

### Task B3: ChartCard.kt (+ LegendItem)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/ChartCard.kt`

- [ ] **Step 1: Tạo ChartCard + LegendItem**

```kotlin
package com.mykiot.pos.core.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.background

data class LegendItem(val label: String, val color: Color)

/** Khung biểu đồ: tiêu đề + slot biểu đồ + legend (chấm màu). */
@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
@Composable
fun ChartCard(
    title: String,
    modifier: Modifier = Modifier,
    legend: List<LegendItem> = emptyList(),
    content: @Composable () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        shadowElevation = 1.dp,
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(12.dp))
            Box(Modifier.fillMaxWidth()) { content() }
            if (legend.isNotEmpty()) {
                Spacer(Modifier.height(12.dp))
                FlowRow(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    legend.forEach { item ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(10.dp).clip(CircleShape).background(item.color))
                            Spacer(Modifier.width(6.dp))
                            Text(item.label, style = MaterialTheme.typography.labelMedium)
                        }
                    }
                }
            }
        }
    }
}
```

> Cần import `androidx.compose.foundation.layout.height`. Thêm `import androidx.compose.foundation.layout.height`.

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/ChartCard.kt
git commit -m "feat(android): component ChartCard + LegendItem"
```

### Task B4: ColumnChart.kt

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/charts/ColumnChart.kt`

- [ ] **Step 1: Tạo ColumnChart (Canvas)**

```kotlin
package com.mykiot.pos.core.ui.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.theme.DataInk

/** Cột dọc đơn giản: nhãn trục X dưới mỗi cột, animate chiều cao khi vào. */
@Composable
fun ColumnChart(
    data: List<Pair<String, Double>>,
    modifier: Modifier = Modifier,
    barColor: Color = DataInk,
) {
    val fractions = ChartMath.normalize(data.map { it.second })
    val anim by animateFloatAsState(
        targetValue = if (data.isEmpty()) 0f else 1f,
        animationSpec = tween(700),
        label = "col-anim",
    )
    Column(modifier.fillMaxWidth()) {
        Canvas(
            Modifier
                .fillMaxWidth()
                .height(160.dp)
                .padding(top = 4.dp),
        ) {
            if (data.isEmpty()) return@Canvas
            val n = data.size
            val gap = size.width * 0.04f
            val barW = (size.width - gap * (n - 1)) / n
            fractions.forEachIndexed { i, f ->
                val h = size.height * f * anim
                val x = i * (barW + gap)
                drawRect(
                    color = barColor,
                    topLeft = Offset(x, size.height - h),
                    size = Size(barW, h),
                )
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 6.dp)) {
            data.forEach { (label, _) ->
                Text(
                    label,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/charts/ColumnChart.kt
git commit -m "feat(android): ColumnChart (Canvas)"
```

### Task B5: DonutChart.kt

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/charts/DonutChart.kt`

- [ ] **Step 1: Tạo DonutChart (Canvas)**

```kotlin
package com.mykiot.pos.core.ui.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

data class DonutSlice(val label: String, val value: Double, val color: Color)

/** Donut: drawArc từng phần, lỗ giữa ~62%, animate sweep. */
@Composable
fun DonutChart(
    slices: List<DonutSlice>,
    modifier: Modifier = Modifier,
) {
    val sweeps = ChartMath.sweepAngles(slices.map { it.value })
    val anim by animateFloatAsState(
        targetValue = if (slices.isEmpty()) 0f else 1f,
        animationSpec = tween(700),
        label = "donut-anim",
    )
    Box(modifier.size(160.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(160.dp)) {
            val stroke = size.minDimension * 0.19f
            val inset = stroke / 2
            var start = -90f
            sweeps.forEachIndexed { i, sweep ->
                drawArc(
                    color = slices[i].color,
                    startAngle = start,
                    sweepAngle = sweep * anim,
                    useCenter = false,
                    topLeft = Offset(inset, inset),
                    size = Size(size.width - stroke, size.height - stroke),
                    style = Stroke(width = stroke),
                )
                start += sweep
            }
        }
    }
}
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/charts/DonutChart.kt
git commit -m "feat(android): DonutChart (Canvas)"
```

### Task B6: HBarChart.kt

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/ui/charts/HBarChart.kt`

- [ ] **Step 1: Tạo HBarChart**

```kotlin
package com.mykiot.pos.core.ui.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.theme.DataInk

/** Thanh ngang top-N: tên + thanh tỉ lệ + giá trị. */
@Composable
fun HBarChart(
    data: List<Pair<String, Double>>,
    valueLabel: (Double) -> String,
    modifier: Modifier = Modifier,
    barColor: Color = DataInk,
) {
    val fractions = ChartMath.normalize(data.map { it.second })
    val anim by animateFloatAsState(
        targetValue = if (data.isEmpty()) 0f else 1f,
        animationSpec = tween(700),
        label = "hbar-anim",
    )
    Column(modifier.fillMaxWidth()) {
        data.forEachIndexed { i, (label, value) ->
            Row(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                Text(
                    label,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    modifier = Modifier.weight(0.42f),
                )
                Box(Modifier.weight(0.58f)) {
                    Box(
                        Modifier
                            .fillMaxWidth(fractions[i] * anim)
                            .height(18.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(barColor),
                    )
                }
            }
            Text(
                valueLabel(value),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 4.dp),
            )
            Spacer(Modifier.height(2.dp))
        }
    }
}
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/charts/HBarChart.kt
git commit -m "feat(android): HBarChart (Canvas)"
```

---

## PHASE C — Dữ liệu Dashboard

### Task C1: DateRanges.kt — last7DaysRange (TDD)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/core/util/DateRanges.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/core/util/DateRangesTest.kt`

- [ ] **Step 1: Test thất bại**

```kotlin
package com.mykiot.pos.core.util

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDate

class DateRangesTest {
    @Test fun `last7DaysRange spans 6 days back to today inclusive`() {
        val today = LocalDate.of(2026, 6, 13)
        val (from, to) = last7DaysRange(today)
        assertEquals("2026-06-07", from)
        assertEquals("2026-06-13", to)
    }
}
```

- [ ] **Step 2: Chạy → FAIL**

Run: `"$GRADLE" :app:testDebugUnitTest --tests "*DateRangesTest*" --console=plain`
Expected: FAIL — hàm chưa có.

- [ ] **Step 3: Viết hàm**

```kotlin
package com.mykiot.pos.core.util

import java.time.LocalDate

/** Trả (from, to) dạng "YYYY-MM-DD": 7 ngày gần nhất kể cả hôm nay. */
fun last7DaysRange(today: LocalDate = LocalDate.now()): Pair<String, String> =
    today.minusDays(6).toString() to today.toString()
```

- [ ] **Step 4: Chạy → PASS**

Run: `"$GRADLE" :app:testDebugUnitTest --tests "*DateRangesTest*" --console=plain`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/util/DateRanges.kt \
        android/app/src/test/java/com/mykiot/pos/core/util/DateRangesTest.kt
git commit -m "feat(android): last7DaysRange helper + test"
```

### Task C2: ReportDtos.kt — RevenueDto, TopProductsDto

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/dto/ReportDtos.kt`

- [ ] **Step 1: Thêm DTO (giữ nguyên DashboardDto/EodMethodRowDto/EndOfDayDto)**

Thêm vào cuối file:

```kotlin
@Serializable
data class RevenuePointDto(
    val period: String,
    val revenue: Double = 0.0,
    val invoices: Int = 0,
    val profit: Double = 0.0,
)

@Serializable
data class RevenueDto(
    @SerialName("total_revenue") val totalRevenue: Double = 0.0,
    @SerialName("total_profit") val totalProfit: Double = 0.0,
    val series: List<RevenuePointDto> = emptyList(),
)

@Serializable
data class TopProductItemDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String,
    val revenue: Double = 0.0,
    @SerialName("quantity_sold") val quantitySold: Double = 0.0,
    val profit: Double = 0.0,
)

@Serializable
data class TopProductsDto(
    val items: List<TopProductItemDto> = emptyList(),
)
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/dto/ReportDtos.kt
git commit -m "feat(android): DTO RevenueDto + TopProductsDto"
```

### Task C3: ReportApi.kt — revenue, topProducts

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/ReportApi.kt`

- [ ] **Step 1: Thay nội dung**

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto
import retrofit2.http.GET
import retrofit2.http.Query

interface ReportApi {
    @GET("reports/dashboard") suspend fun dashboard(): DashboardDto
    @GET("reports/end-of-day") suspend fun endOfDay(@Query("date") date: String? = null): EndOfDayDto

    @GET("reports/revenue")
    suspend fun revenue(
        @Query("from") from: String,
        @Query("to") to: String,
        @Query("group_by") groupBy: String = "day",
    ): RevenueDto

    @GET("reports/top-products")
    suspend fun topProducts(
        @Query("from") from: String? = null,
        @Query("to") to: String? = null,
        @Query("limit") limit: Int = 5,
    ): TopProductsDto
}
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/ReportApi.kt
git commit -m "feat(android): ReportApi thêm revenue + topProducts"
```

### Task C4: ReportRepository — revenueLast7Days, topProducts

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/report/data/ReportRepository.kt`

- [ ] **Step 1: Thêm 2 hàm (giữ dashboard/endOfDay cũ)**

Thêm import + 2 hàm:

```kotlin
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto
import com.mykiot.pos.core.util.last7DaysRange
```

```kotlin
    open suspend fun revenueLast7Days(): ApiResult<RevenueDto> {
        val (from, to) = last7DaysRange()
        return runCatching { reportApi.revenue(from = from, to = to, groupBy = "day") }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
    }

    open suspend fun topProducts(limit: Int = 5): ApiResult<TopProductsDto> =
        runCatching { reportApi.topProducts(limit = limit) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/report/data/ReportRepository.kt
git commit -m "feat(android): ReportRepository revenueLast7Days + topProducts"
```

### Task C5: ReportUiState — thêm trường

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/report/ReportUiState.kt`

- [ ] **Step 1: Thay nội dung**

```kotlin
package com.mykiot.pos.feature.report

import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto

data class ReportUiState(
    val dashboard: DashboardDto? = null,
    val eod: EndOfDayDto? = null,           // null nếu CASHIER (403) hoặc chưa tải
    val revenue7d: RevenueDto? = null,      // null nếu CASHIER (403)
    val topProducts: TopProductsDto? = null,// null nếu CASHIER (403)
    val loading: Boolean = false,
    val errorMessage: String? = null,
)
```

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/report/ReportUiState.kt
git commit -m "feat(android): ReportUiState thêm revenue7d + topProducts"
```

### Task C6: ReportViewModel — load role-aware (TDD)

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/report/ReportViewModel.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/feature/report/ReportViewModelTest.kt`

- [ ] **Step 1: Viết test thất bại**

```kotlin
package com.mykiot.pos.feature.report

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto
import com.mykiot.pos.feature.report.data.ReportRepository
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

class ReportViewModelTest {
    private val repo = mockk<ReportRepository>()
    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun dash() = DashboardDto(
        todayRevenue = "100000", todayInvoices = 3, todayCustomers = 2,
        pendingDrafts = 0, lowStockCount = 1, outOfStockCount = 0,
    )

    @Test
    fun `cashier 403 keeps charts null but loads dashboard`() = runTest {
        coEvery { repo.dashboard() } returns ApiResult.Success(dash())
        coEvery { repo.endOfDay() } returns ApiResult.Failure(ApiError("FORBIDDEN", "403"))
        coEvery { repo.revenueLast7Days() } returns ApiResult.Failure(ApiError("FORBIDDEN", "403"))
        coEvery { repo.topProducts(any()) } returns ApiResult.Failure(ApiError("FORBIDDEN", "403"))
        val vm = ReportViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(3, vm.state.value.dashboard?.todayInvoices)
        assertNull(vm.state.value.revenue7d)
        assertNull(vm.state.value.topProducts)
        assertNull(vm.state.value.eod)
    }

    @Test
    fun `owner gets charts data`() = runTest {
        coEvery { repo.dashboard() } returns ApiResult.Success(dash())
        coEvery { repo.endOfDay() } returns ApiResult.Failure(ApiError("X", "skip"))
        coEvery { repo.revenueLast7Days() } returns ApiResult.Success(
            RevenueDto(totalRevenue = 500000.0, series = emptyList()),
        )
        coEvery { repo.topProducts(any()) } returns ApiResult.Success(TopProductsDto(items = emptyList()))
        val vm = ReportViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(500000.0, vm.state.value.revenue7d?.totalRevenue ?: 0.0, 0.001)
        assertEquals(0, vm.state.value.topProducts?.items?.size)
    }
}
```

> Kiểm tra constructor `DashboardDto` (xem `ReportDtos.kt`): các tham số `todayRevenue` (String), `todayInvoices`, `todayProfit` (nullable, để mặc định), `todayCustomers`, `pendingDrafts`, `lowStockCount`, `outOfStockCount`, `inventoryValue` (nullable). Bỏ qua tham số nullable có default.

- [ ] **Step 2: Chạy → FAIL**

Run: `"$GRADLE" :app:testDebugUnitTest --tests "*ReportViewModelTest*" --console=plain`
Expected: FAIL — VM chưa load revenue/topProducts (state null khác kỳ vọng owner-case).

- [ ] **Step 3: Cập nhật ViewModel**

Thay hàm `load()` trong `ReportViewModel.kt` (giữ phần dashboard + eod cũ, thêm revenue + topProducts):

```kotlin
    fun load() {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.dashboard()) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, dashboard = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
            // Các nguồn OWNER-only: 403 (CASHIER) → bỏ qua, không báo lỗi.
            when (val e = repository.endOfDay()) {
                is ApiResult.Success -> _state.update { it.copy(eod = e.data) }
                is ApiResult.Failure -> _state.update { it.copy(eod = null) }
            }
            when (val rev = repository.revenueLast7Days()) {
                is ApiResult.Success -> _state.update { it.copy(revenue7d = rev.data) }
                is ApiResult.Failure -> _state.update { it.copy(revenue7d = null) }
            }
            when (val tp = repository.topProducts(5)) {
                is ApiResult.Success -> _state.update { it.copy(topProducts = tp.data) }
                is ApiResult.Failure -> _state.update { it.copy(topProducts = null) }
            }
        }
    }
```

- [ ] **Step 4: Chạy → PASS**

Run: `"$GRADLE" :app:testDebugUnitTest --tests "*ReportViewModelTest*" --console=plain`
Expected: PASS (2 test).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/report/ReportViewModel.kt \
        android/app/src/test/java/com/mykiot/pos/feature/report/ReportViewModelTest.kt
git commit -m "feat(android): ReportViewModel load role-aware (revenue/top/eod) + test"
```

---

## PHASE D — Màn hình

### Task D1: ReportScreen — KPI grid + 3 ChartCard

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/report/ReportScreen.kt`

- [ ] **Step 1: Viết lại ReportScreen**

```kotlin
package com.mykiot.pos.feature.report

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material.icons.outlined.TrendingUp
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.network.dto.EodMethodRowDto
import com.mykiot.pos.core.ui.ChartCard
import com.mykiot.pos.core.ui.KpiTile
import com.mykiot.pos.core.ui.LegendItem
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.SectionHeader
import com.mykiot.pos.core.ui.Spacing
import com.mykiot.pos.core.ui.charts.ColumnChart
import com.mykiot.pos.core.ui.charts.DonutChart
import com.mykiot.pos.core.ui.charts.DonutSlice
import com.mykiot.pos.core.ui.charts.HBarChart
import com.mykiot.pos.core.ui.theme.DataBank
import com.mykiot.pos.core.ui.theme.DataCash
import com.mykiot.pos.core.ui.theme.DataOther
import com.mykiot.pos.core.ui.theme.DataProfit
import com.mykiot.pos.core.ui.theme.DataWallet
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ReportScreen(viewModel: ReportViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding)
                .padding(horizontal = Spacing.lg, vertical = Spacing.md)
                .verticalScroll(rememberScrollState()),
        ) {
            val d = state.dashboard
            if (d != null) {
                SectionHeader("Hôm nay")
                Spacer(Modifier.height(Spacing.md))
                // Lưới KPI 2 cột
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    KpiTile(Icons.Outlined.TrendingUp, "Doanh thu", formatVnd(d.todayRevenue), Modifier.weight(1f))
                    KpiTile(Icons.Outlined.Description, "Số hóa đơn", d.todayInvoices.toString(), Modifier.weight(1f))
                }
                Spacer(Modifier.height(Spacing.md))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    KpiTile(Icons.Outlined.Group, "Khách hàng", d.todayCustomers.toString(), Modifier.weight(1f))
                    KpiTile(
                        Icons.Outlined.Inventory2, "Hàng sắp hết", d.lowStockCount.toString(),
                        Modifier.weight(1f), caption = "hết: ${d.outOfStockCount}",
                    )
                }
                d.todayProfit?.let { profit ->
                    Spacer(Modifier.height(Spacing.md))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                        KpiTile(Icons.Outlined.Payments, "Lợi nhuận", formatVnd(profit), Modifier.weight(1f), accent = DataProfit)
                        Spacer(Modifier.weight(1f))
                    }
                }
            }

            // Biểu đồ doanh thu 7 ngày (OWNER)
            state.revenue7d?.let { rev ->
                Spacer(Modifier.height(Spacing.xl))
                ChartCard(title = "Doanh thu 7 ngày") {
                    ColumnChart(data = rev.series.map { shortDay(it.period) to it.revenue })
                }
            }

            // Cơ cấu thanh toán (OWNER)
            state.eod?.by_method?.takeIf { it.isNotEmpty() }?.let { rows ->
                Spacer(Modifier.height(Spacing.lg))
                val slices = rows.map { DonutSlice(methodLabel(it.method), paymentValue(it), methodColor(it.method)) }
                ChartCard(
                    title = "Cơ cấu thanh toán",
                    legend = slices.map { LegendItem(it.label, it.color) },
                ) {
                    DonutChart(slices = slices)
                }
            }

            // Top sản phẩm (OWNER)
            state.topProducts?.items?.takeIf { it.isNotEmpty() }?.let { items ->
                Spacer(Modifier.height(Spacing.lg))
                ChartCard(title = "Top sản phẩm") {
                    HBarChart(
                        data = items.take(5).map { it.productName to it.revenue },
                        valueLabel = { formatVnd(it.toString()) },
                    )
                }
            }
            Spacer(Modifier.height(Spacing.xl))
        }
    }

    LoadingDialog(visible = state.loading && state.dashboard == null, message = "Đang tải báo cáo...")
}

/** "2026-06-13" → "13/6" cho nhãn trục. */
private fun shortDay(period: String): String {
    val parts = period.split("-")
    return if (parts.size == 3) "${parts[2].toInt()}/${parts[1].toInt()}" else period
}

private fun methodLabel(m: String) = when (m) {
    "CASH" -> "Tiền mặt"
    "BANK_TRANSFER" -> "Chuyển khoản"
    "MOMO" -> "MoMo"
    "VNPAY" -> "VNPay"
    else -> m
}

private fun methodColor(m: String) = when (m) {
    "CASH" -> DataCash
    "BANK_TRANSFER" -> DataBank
    "MOMO" -> DataWallet
    else -> DataOther
}

/** Tiền vào theo phương thức trong ngày = total_in. */
private fun paymentValue(row: EodMethodRowDto): Double = row.totalIn.toDoubleOrNull() ?: 0.0
```

> **Kiểm tra trước khi viết** (`ReportDtos.kt`): tên field `by_method` (snake hoặc camel?). Trong DTO hiện tại là `@SerialName("by_method") val byMethod`. Nếu vậy đổi `state.eod?.by_method` → `state.eod?.byMethod`, và `row.totalIn` đã đúng (`@SerialName("total_in") val totalIn: String`). Sửa cho khớp tên Kotlin thực tế.

- [ ] **Step 2: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL. (Nếu lỗi tên field `byMethod`/`totalIn`, chỉnh theo DTO thật rồi build lại.)

- [ ] **Step 3: Chạy toàn bộ test (đảm bảo không vỡ)**

Run: `"$GRADLE" :app:testDebugUnitTest --console=plain`
Expected: BUILD SUCCESSFUL (mọi test pass; nếu có test receipt fail do thay đổi chưa commit của repo — không liên quan task này — ghi nhận và bỏ qua).

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/report/ReportScreen.kt
git commit -m "feat(android): Dashboard mới — lưới KPI + 3 biểu đồ màu (role-aware)"
```

### Task D2: HubScreen — icon Outlined + elevation + chevron

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt`

- [ ] **Step 1: Đổi import icon Filled → Outlined**

Thay khối import icon hiện tại bằng:

```kotlin
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.AssignmentReturn
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.Assessment
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.PointOfSale
import androidx.compose.material.icons.outlined.Sell
```

- [ ] **Step 2: Cập nhật `hubGroups` dùng icon Outlined**

Thay các tham chiếu icon trong `hubGroups`:

```kotlin
private val hubGroups = listOf(
    HubGroup(
        "Kho",
        listOf(
            HubItem("Nhập hàng", Routes.RECEIPT, Icons.AutoMirrored.Outlined.ReceiptLong),
            HubItem("Tồn kho", Routes.INVENTORY, Icons.Outlined.Inventory2),
            HubItem("Trả hàng", Routes.RETURNS, Icons.AutoMirrored.Outlined.AssignmentReturn),
        ),
    ),
    HubGroup(
        "Danh mục",
        listOf(
            HubItem("Sản phẩm", Routes.PRODUCTS, Icons.Outlined.Sell),
            HubItem("Khách hàng", Routes.CUSTOMERS, Icons.Outlined.Group),
        ),
    ),
    HubGroup(
        "Bán hàng",
        listOf(
            HubItem("Hóa đơn", Routes.INVOICE_HISTORY, Icons.Outlined.Description),
        ),
    ),
    HubGroup(
        "Báo cáo",
        listOf(
            HubItem("Tổng quan", Routes.REPORT, Icons.Outlined.Assessment),
        ),
    ),
    HubGroup(
        "Hệ thống",
        listOf(
            HubItem("Đổi mật khẩu", Routes.CHANGE_PASSWORD, Icons.Outlined.Lock),
        ),
    ),
)
```

Và trong `PosButton`, đổi `Icons.Filled.PointOfSale` → `Icons.Outlined.PointOfSale`.

- [ ] **Step 3: Thêm elevation + chevron cho HubCard**

Thay thân hàm `HubCard` — thêm `shadowElevation = 1.dp` vào `Surface`, và đặt chevron mảnh ở góc:

```kotlin
@Composable
private fun HubCard(item: HubItem, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        shadowElevation = 1.dp,
        modifier = Modifier
            .fillMaxWidth()
            .height(96.dp),
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .padding(14.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Icon(
                    item.icon,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface,
                )
                Icon(
                    Icons.Outlined.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.outline,
                )
            }
            Text(
                item.label,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}
```

Thêm import nếu thiếu: `androidx.compose.foundation.layout.Row`, `androidx.compose.ui.Alignment`.

- [ ] **Step 4: Thêm shadow cho PosButton**

Trong `PosButton`, thêm `shadowElevation = 2.dp` vào `Surface`.

- [ ] **Step 5: Biên dịch**

Run: `"$GRADLE" :app:compileDebugKotlin --console=plain`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 6: Verify thủ công + commit**

Mở app: Hub có icon outline mảnh, card nổi nhẹ + chevron, nút POS có bóng. Vào Báo cáo (OWNER) thấy KPI + 3 biểu đồ màu; CASHIER chỉ thấy KPI.

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt
git commit -m "feat(android): Hub polish — icon Outlined + elevation + chevron"
```

---

## Self-Review

- **Spec coverage:** §1 màu→A1/A2; §2 icon→D2; §3 Material tokens→A3/A4 + elevation trong B2/B3/D2; §4 component→B2..B6; §5 Hub→D2; §6 Dashboard + API→C1..C6 + D1. Không thiếu mục.
- **Placeholder scan:** không có TODO/“tương tự task”; mọi step có code thật.
- **Type consistency:** `ChartMath.normalize/sweepAngles`, `DonutSlice(label,value,color)`, `LegendItem(label,color)`, `KpiTile(icon,label,value,modifier,accent,caption)`, `HBarChart(data,valueLabel,modifier,barColor)`, `ColumnChart(data,modifier,barColor)` — dùng nhất quán giữa B và D.
- **Điểm cần kiểm khi execute (kiểm chứng codebase, không phải placeholder):** tên field Kotlin của `EndOfDayDto` (`byMethod`/`totalIn` theo `@SerialName`); danh sách tham số constructor `DashboardDto` khi viết test; sự tồn tại các icon `Icons.Outlined.*` đã liệt kê (đều thuộc material-icons-extended đã có).
```
