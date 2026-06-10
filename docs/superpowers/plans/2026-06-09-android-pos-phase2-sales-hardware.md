# Android POS — Phase 2: Bán hàng (POS) + Phần cứng

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Màn bán hàng hoàn chỉnh: tìm/quét SP → giỏ hàng (+1, gộp dòng) → chọn KH → thanh toán đa phương thức → in bill 58mm; kèm quét camera ML Kit, súng HID, và máy in ESC/POS bluetooth.

**Architecture:** Tiếp nối Phase 1 (Compose + MVVM + Hilt + Retrofit). Thêm `feature/pos`, các API (`ProductApi`, `CustomerApi`, `SalesApi`), domain giỏ hàng thuần Kotlin (TDD), và `core/hardware` (scanner + printer) sau interface để test logic không cần thiết bị.

**Tech bổ sung:** CameraX + ML Kit barcode-scanning; ESCPOS-ThermalPrinter-Android (DantSu); quyền CAMERA + BLUETOOTH_CONNECT.

**Phụ thuộc backend (online-only, không đổi BE):** `GET /products/search?q=`, `GET /products/barcode/{code}` (trả `matched_unit`), `GET /customers?search=`, `GET /customers/phone/{phone}`, `POST /invoices`, `PUT /invoices/{id}`, `POST /invoices/{id}/complete`, `GET /invoices/drafts`, `GET /invoices/{id}`.

---

## Thêm thư viện (libs.versions.toml)

```toml
# [versions] thêm:
camerax = "1.4.1"
mlkitBarcode = "17.3.0"
escpos = "3.4.0"
accompanistPermissions = "0.36.0"

# [libraries] thêm:
camera-camera2 = { module = "androidx.camera:camera-camera2", version.ref = "camerax" }
camera-lifecycle = { module = "androidx.camera:camera-lifecycle", version.ref = "camerax" }
camera-view = { module = "androidx.camera:camera-view", version.ref = "camerax" }
mlkit-barcode = { module = "com.google.mlkit:barcode-scanning", version.ref = "mlkitBarcode" }
escpos-thermal = { module = "com.github.DantSu:ESCPOS-ThermalPrinter-Android", version.ref = "escpos" }
accompanist-permissions = { module = "com.google.accompanist:accompanist-permissions", version.ref = "accompanistPermissions" }
```

`settings.gradle.kts` — thêm JitPack cho ESCPOS lib:
```kotlin
dependencyResolutionManagement {
    repositories {
        google(); mavenCentral()
        maven { url = uri("https://jitpack.io") }
    }
}
```

`app/build.gradle.kts` — thêm vào `dependencies`:
```kotlin
implementation(libs.camera.camera2)
implementation(libs.camera.lifecycle)
implementation(libs.camera.view)
implementation(libs.mlkit.barcode)
implementation(libs.escpos.thermal)
implementation(libs.accompanist.permissions)
```

`AndroidManifest.xml` — thêm quyền (trên thẻ `<application>`):
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera" android:required="false" />
<uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
```

---

## File Structure (Phase 2)

- `core/network/dto/ProductDtos.kt`, `CustomerDtos.kt`, `SalesDtos.kt`
- `core/network/ProductApi.kt`, `CustomerApi.kt`, `SalesApi.kt` + provide trong `NetworkModule`
- `core/util/Money.kt` — định dạng VND
- `feature/pos/cart/CartLine.kt`, `Cart.kt` — domain thuần (TDD)
- `feature/pos/data/PosRepository.kt`
- `feature/pos/PosViewModel.kt`, `PosUiState.kt`
- `feature/pos/PosScreen.kt`, `CartLineRow.kt`, `PaymentDialog.kt`, `CustomerPickerDialog.kt`, `DraftListSheet.kt`
- `core/hardware/scanner/BarcodeScanner.kt` (interface) + `MlKitScannerScreen.kt` (CameraX UI) + `HidScanField.kt`
- `core/hardware/printer/ReceiptPrinter.kt` (interface), `EscPosReceiptPrinter.kt`, `ReceiptLayout.kt` (TDD)
- `navigation`: gắn `PosScreen` vào tab Bán
- Tests: `CartTest.kt`, `ReceiptLayoutTest.kt`, `PosViewModelTest.kt`, `MoneyTest.kt`

---

## Task 1: DTOs + APIs (Product / Customer / Sales)

**Files:** dto/`ProductDtos.kt`, `CustomerDtos.kt`, `SalesDtos.kt`; `ProductApi.kt`, `CustomerApi.kt`, `SalesApi.kt`; provide trong `NetworkModule`.

- [ ] **Step 1:** Tạo `ProductDtos.kt` (khớp `ProductBriefResponse` + `ProductUnitResponse`):

```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ProductUnitDto(
    val id: Long,
    @SerialName("unit_name") val unitName: String,
    @SerialName("conversion_rate") val conversionRate: Double,
    @SerialName("sale_price") val salePrice: Double? = null,
    val barcode: String? = null,
)

@Serializable
data class ProductBriefDto(
    val id: Long,
    val sku: String,
    val barcode: String? = null,
    val name: String,
    val unit: String,
    @SerialName("sale_price") val salePrice: Double,
    @SerialName("cost_price") val costPrice: Double? = null,
    @SerialName("image_url") val imageUrl: String? = null,
    @SerialName("allow_negative") val allowNegative: Boolean = false,
    val status: String,
    val units: List<ProductUnitDto> = emptyList(),
    @SerialName("matched_unit") val matchedUnit: ProductUnitDto? = null,
)

@Serializable
data class ProductSearchDto(val items: List<ProductBriefDto> = emptyList())
```

- [ ] **Step 2:** Tạo `CustomerDtos.kt`:

```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CustomerDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    @SerialName("total_spent") val totalSpent: Double = 0.0,
    @SerialName("total_orders") val totalOrders: Int = 0,
)

@Serializable
data class CustomerListDto(val items: List<CustomerDto> = emptyList())
```

- [ ] **Step 3:** Tạo `SalesDtos.kt` (khớp sales/schemas.py):

```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class InvoiceItemInputDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("unit_id") val unitId: Long? = null,
    val quantity: String,                       // Decimal as string để tránh sai số
    @SerialName("unit_price") val unitPrice: String? = null,
    @SerialName("discount_amount") val discountAmount: String = "0",
)

@Serializable
data class InvoiceCreateDto(
    @SerialName("customer_id") val customerId: Long? = null,
    val items: List<InvoiceItemInputDto> = emptyList(),
    @SerialName("discount_amount") val discountAmount: String = "0",
    val note: String? = null,
)

@Serializable
data class PaymentInputDto(
    val method: String,                         // CASH | BANK_TRANSFER | MOMO | VNPAY | OTHER
    val amount: String,
    val note: String? = null,
)

@Serializable
data class InvoiceCompleteDto(
    val payments: List<PaymentInputDto> = emptyList(),
    @SerialName("allow_debt") val allowDebt: Boolean = false,
)

@Serializable
data class InvoiceItemDto(
    val id: Long,
    @SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String,
    @SerialName("product_sku") val productSku: String,
    val unit: String? = null,
    @SerialName("unit_id") val unitId: Long? = null,
    val quantity: String,
    @SerialName("unit_price") val unitPrice: String,
    @SerialName("discount_amount") val discountAmount: String,
    @SerialName("line_total") val lineTotal: String,
)

@Serializable
data class InvoiceDto(
    val id: Long,
    val code: String,
    @SerialName("customer_id") val customerId: Long? = null,
    @SerialName("customer_name") val customerName: String? = null,
    val subtotal: String,
    @SerialName("discount_amount") val discountAmount: String,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    @SerialName("change_amount") val changeAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    val items: List<InvoiceItemDto> = emptyList(),
)

@Serializable
data class InvoiceBriefDto(
    val id: Long,
    val code: String,
    @SerialName("customer_name") val customerName: String? = null,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    val status: String,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class InvoiceDraftListDto(val items: List<InvoiceBriefDto> = emptyList())
```

- [ ] **Step 4:** Tạo các API interface:

```kotlin
// ProductApi.kt
package com.mykiot.pos.core.network
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductSearchDto
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query
interface ProductApi {
    @GET("products/search") suspend fun search(@Query("q") q: String): ProductSearchDto
    @GET("products/barcode/{code}") suspend fun byBarcode(@Path("code") code: String): ProductBriefDto
}
```
```kotlin
// CustomerApi.kt
package com.mykiot.pos.core.network
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.core.network.dto.CustomerListDto
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query
interface CustomerApi {
    @GET("customers") suspend fun list(@Query("search") search: String? = null): CustomerListDto
    @GET("customers/phone/{phone}") suspend fun byPhone(@Path("phone") phone: String): CustomerDto
}
```
```kotlin
// SalesApi.kt
package com.mykiot.pos.core.network
import com.mykiot.pos.core.network.dto.InvoiceCompleteDto
import com.mykiot.pos.core.network.dto.InvoiceCreateDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceDraftListDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
interface SalesApi {
    @POST("invoices") suspend fun create(@Body body: InvoiceCreateDto): InvoiceDto
    @GET("invoices/{id}") suspend fun get(@Path("id") id: Long): InvoiceDto
    @POST("invoices/{id}/complete") suspend fun complete(@Path("id") id: Long, @Body body: InvoiceCompleteDto): InvoiceDto
    @GET("invoices/drafts") suspend fun drafts(): InvoiceDraftListDto
}
```

- [ ] **Step 5:** Provide trong `NetworkModule` (thêm hàm):
```kotlin
@Provides @Singleton fun productApi(retrofit: Retrofit): ProductApi = retrofit.create(ProductApi::class.java)
@Provides @Singleton fun customerApi(retrofit: Retrofit): CustomerApi = retrofit.create(CustomerApi::class.java)
@Provides @Singleton fun salesApi(retrofit: Retrofit): SalesApi = retrofit.create(SalesApi::class.java)
```

- [ ] **Step 6: Commit** `feat(android): API products/customers/sales cho POS`

---

## Task 2: Money util (TDD)

**Files:** `core/util/Money.kt`, test `MoneyTest.kt`

- [ ] **Step 1: Test (fail)** `MoneyTest.kt`:
```kotlin
package com.mykiot.pos.core.util
import org.junit.Assert.assertEquals
import org.junit.Test
class MoneyTest {
    @Test fun `formats VND with thousands separator and dong suffix`() {
        assertEquals("1.000 đ", formatVnd(1000))
        assertEquals("0 đ", formatVnd(0))
        assertEquals("1.234.567 đ", formatVnd(1234567))
    }
    @Test fun `formats from string decimal`() {
        assertEquals("12.500 đ", formatVnd("12500.00"))
    }
}
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Impl** `Money.kt`:
```kotlin
package com.mykiot.pos.core.util

import java.math.BigDecimal

/** "1.234.567 đ" — dấu chấm ngăn nghìn, kiểu VN. */
fun formatVnd(amount: Long): String {
    val s = kotlin.math.abs(amount).toString().reversed().chunked(3).joinToString(".").reversed()
    val sign = if (amount < 0) "-" else ""
    return "$sign$s đ"
}

fun formatVnd(decimalString: String): String =
    formatVnd(BigDecimal(decimalString).setScale(0, java.math.RoundingMode.HALF_UP).toLong())
```
- [ ] **Step 4:** Run → PASS. **Commit.**

---

## Task 3: Cart domain (TDD — phần lõi nhất)

Giỏ hàng là logic thuần Kotlin: thêm SP (+1), gộp dòng theo (productId, unitId), sửa số lượng/giá/giảm giá, tính tổng. KHÔNG phụ thuộc Android → test JVM thuần.

**Files:** `feature/pos/cart/CartLine.kt`, `Cart.kt`; test `CartTest.kt`

- [ ] **Step 1: Test (fail)** `CartTest.kt`:
```kotlin
package com.mykiot.pos.feature.pos.cart

import org.junit.Assert.assertEquals
import org.junit.Test
import java.math.BigDecimal

class CartTest {

    private fun line(pid: Long, unitId: Long?, qty: String, price: String) =
        CartLine(
            productId = pid, unitId = unitId, name = "SP$pid", sku = "SKU$pid",
            unitName = "cái", unitPrice = BigDecimal(price), quantity = BigDecimal(qty),
        )

    @Test fun `add scanned product appends with qty 1`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
        assertEquals(1, cart.lines.size)
        assertEquals(BigDecimal("1"), cart.lines.first().quantity)
    }

    @Test fun `scanning same product and unit again increments qty`() {
        val cart = Cart()
            .addScanned(line(1, null, "1", "10000"))
            .addScanned(line(1, null, "1", "10000"))
        assertEquals(1, cart.lines.size)
        assertEquals(BigDecimal("2"), cart.lines.first().quantity)
    }

    @Test fun `same product different unit creates separate line`() {
        val cart = Cart()
            .addScanned(line(1, null, "1", "10000"))
            .addScanned(line(1, 5, "1", "240000"))
        assertEquals(2, cart.lines.size)
    }

    @Test fun `setQuantity replaces and supports decimals for weighed goods`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
            .setQuantity(0, BigDecimal("1.5"))
        assertEquals(BigDecimal("1.5"), cart.lines.first().quantity)
    }

    @Test fun `removeLine drops it`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
            .addScanned(line(2, null, "1", "5000"))
            .removeLine(0)
        assertEquals(1, cart.lines.size)
        assertEquals(2L, cart.lines.first().productId)
    }

    @Test fun `lineTotal = qty x price - discount; subtotal sums lines`() {
        val cart = Cart()
            .addScanned(line(1, null, "2", "10000"))        // 20000
            .addScanned(line(2, null, "1", "5000"))         // 5000
            .setLineDiscount(0, BigDecimal("2000"))         // 18000
        assertEquals(BigDecimal("18000"), cart.lines[0].lineTotal())
        assertEquals(BigDecimal("23000"), cart.subtotal())
    }

    @Test fun `total applies invoice-level discount, never below zero`() {
        val cart = Cart()
            .addScanned(line(1, null, "1", "10000"))
            .withInvoiceDiscount(BigDecimal("3000"))
        assertEquals(BigDecimal("7000"), cart.total())
    }

    @Test fun `changeAmount = paid - total clamped at zero`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
        assertEquals(BigDecimal("5000"), cart.changeFor(BigDecimal("15000")))
        assertEquals(BigDecimal.ZERO, cart.changeFor(BigDecimal("8000")))
    }
}
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Impl** `CartLine.kt`:
```kotlin
package com.mykiot.pos.feature.pos.cart

import java.math.BigDecimal

data class CartLine(
    val productId: Long,
    val unitId: Long?,            // null = đơn vị cơ bản
    val name: String,
    val sku: String,
    val unitName: String,
    val unitPrice: BigDecimal,
    val quantity: BigDecimal,
    val discount: BigDecimal = BigDecimal.ZERO,
) {
    fun lineTotal(): BigDecimal =
        (unitPrice.multiply(quantity)).subtract(discount).max(BigDecimal.ZERO)

    /** Cùng SP + cùng đơn vị → được gộp khi quét lại. */
    fun sameItem(other: CartLine): Boolean =
        productId == other.productId && unitId == other.unitId
}
```
`Cart.kt`:
```kotlin
package com.mykiot.pos.feature.pos.cart

import java.math.BigDecimal

data class Cart(
    val lines: List<CartLine> = emptyList(),
    val invoiceDiscount: BigDecimal = BigDecimal.ZERO,
) {
    fun addScanned(line: CartLine): Cart {
        val idx = lines.indexOfFirst { it.sameItem(line) }
        return if (idx >= 0) {
            val merged = lines[idx].copy(quantity = lines[idx].quantity.add(line.quantity))
            copy(lines = lines.toMutableList().also { it[idx] = merged })
        } else {
            copy(lines = lines + line)
        }
    }

    fun setQuantity(index: Int, qty: BigDecimal): Cart =
        mutate(index) { it.copy(quantity = qty.max(BigDecimal.ZERO)) }

    fun setUnitPrice(index: Int, price: BigDecimal): Cart =
        mutate(index) { it.copy(unitPrice = price.max(BigDecimal.ZERO)) }

    fun setLineDiscount(index: Int, discount: BigDecimal): Cart =
        mutate(index) { it.copy(discount = discount.max(BigDecimal.ZERO)) }

    fun removeLine(index: Int): Cart =
        copy(lines = lines.toMutableList().also { it.removeAt(index) })

    fun withInvoiceDiscount(discount: BigDecimal): Cart =
        copy(invoiceDiscount = discount.max(BigDecimal.ZERO))

    fun clear(): Cart = Cart()

    fun subtotal(): BigDecimal =
        lines.fold(BigDecimal.ZERO) { acc, l -> acc.add(l.lineTotal()) }

    fun total(): BigDecimal = subtotal().subtract(invoiceDiscount).max(BigDecimal.ZERO)

    fun changeFor(paid: BigDecimal): BigDecimal = paid.subtract(total()).max(BigDecimal.ZERO)

    fun isEmpty(): Boolean = lines.isEmpty()

    private fun mutate(index: Int, f: (CartLine) -> CartLine): Cart =
        copy(lines = lines.toMutableList().also { it[index] = f(it[index]) })
}
```
- [ ] **Step 4:** Run → PASS. **Commit** `feat(android): domain giỏ hàng POS (TDD)`.

---

## Task 4: ReceiptLayout (bill 58mm — TDD)

Render bill thành các dòng text ≤32 ký tự (khổ 58mm). Logic thuần → TDD. In bitmap/ESC-POS dùng layout này.

**Files:** `core/hardware/printer/ReceiptLayout.kt`, test `ReceiptLayoutTest.kt`

- [ ] **Step 1: Test (fail)** `ReceiptLayoutTest.kt`:
```kotlin
package com.mykiot.pos.core.hardware.printer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ReceiptLayoutTest {

    private val data = ReceiptData(
        shopName = "TAP HOA ABC",
        shopPhone = "0901234567",
        invoiceCode = "HD20260609-001",
        dateTime = "09/06/2026 21:30",
        lines = listOf(
            ReceiptItemLine("Mi tom Hao Hao", qty = "2", unitPrice = "4.000", lineTotal = "8.000"),
            ReceiptItemLine("Nuoc ngot Coca 330ml", qty = "1", unitPrice = "10.000", lineTotal = "10.000"),
        ),
        total = "18.000 đ",
        paid = "20.000 đ",
        change = "2.000 đ",
        footer = "Cam on quy khach!",
    )

    @Test fun `every rendered line fits 32 chars`() {
        ReceiptLayout.render(data, width = 32).forEach {
            assertTrue("Quá dài: '$it' (${it.length})", it.length <= 32)
        }
    }

    @Test fun `contains shop name, code and total`() {
        val text = ReceiptLayout.render(data, width = 32).joinToString("\n")
        assertTrue(text.contains("TAP HOA ABC"))
        assertTrue(text.contains("HD20260609-001"))
        assertTrue(text.contains("18.000 đ"))
        assertTrue(text.contains("Cam on quy khach!"))
    }

    @Test fun `right-aligns total amount on its own row`() {
        val totalRow = ReceiptLayout.render(data, width = 32).first { it.contains("TONG") }
        assertEquals(32, totalRow.length)
        assertTrue(totalRow.trimEnd().endsWith("18.000 đ"))
    }
}
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Impl** `ReceiptLayout.kt`:
```kotlin
package com.mykiot.pos.core.hardware.printer

data class ReceiptItemLine(
    val name: String,
    val qty: String,
    val unitPrice: String,
    val lineTotal: String,
)

data class ReceiptData(
    val shopName: String,
    val shopPhone: String?,
    val invoiceCode: String,
    val dateTime: String,
    val lines: List<ReceiptItemLine>,
    val total: String,
    val paid: String,
    val change: String,
    val footer: String?,
)

object ReceiptLayout {

    fun render(data: ReceiptData, width: Int = 32): List<String> {
        val out = mutableListOf<String>()
        out += center(data.shopName, width)
        data.shopPhone?.let { out += center("DT: $it", width) }
        out += "-".repeat(width)
        out += data.invoiceCode
        out += data.dateTime
        out += "-".repeat(width)
        data.lines.forEach { item ->
            // dòng 1: tên SP (cắt nếu dài)
            out += clip(item.name, width)
            // dòng 2: "  qty x unitPrice" trái, lineTotal phải
            val left = "  ${item.qty} x ${item.unitPrice}"
            out += leftRight(left, item.lineTotal, width)
        }
        out += "-".repeat(width)
        out += leftRight("TONG", data.total, width)
        out += leftRight("Khach dua", data.paid, width)
        out += leftRight("Thoi lai", data.change, width)
        data.footer?.let { out += "-".repeat(width); out += center(it, width) }
        return out
    }

    private fun clip(s: String, width: Int) = if (s.length <= width) s else s.substring(0, width)

    private fun center(s: String, width: Int): String {
        val c = clip(s, width)
        val pad = (width - c.length) / 2
        return (" ".repeat(pad) + c).let { it + " ".repeat(width - it.length) }
    }

    private fun leftRight(left: String, right: String, width: Int): String {
        val l = clip(left, width)
        val maxRight = width - l.length
        val r = if (right.length > maxRight) right.substring(0, maxRight.coerceAtLeast(0)) else right
        val gap = width - l.length - r.length
        return l + " ".repeat(gap.coerceAtLeast(0)) + r
    }
}
```
- [ ] **Step 4:** Run → PASS. **Commit** `feat(android): layout bill 58mm (TDD)`.

---

## Task 5: Hardware interfaces (scanner + printer) + impl

`ReceiptPrinter` và `BarcodeScanner` là interface để màn/VM phụ thuộc abstraction. Impl dùng thiết bị thật → chỉ smoke test thủ công.

**Files:** `core/hardware/scanner/BarcodeScanner.kt`, `MlKitScannerScreen.kt`, `HidScanField.kt`; `core/hardware/printer/ReceiptPrinter.kt`, `EscPosReceiptPrinter.kt`; provide trong Hilt.

- [ ] **Step 1:** `ReceiptPrinter.kt` (interface) + result type:
```kotlin
package com.mykiot.pos.core.hardware.printer

sealed interface PrintResult {
    data object Ok : PrintResult
    data class Error(val message: String) : PrintResult   // tiếng Việt
}

interface ReceiptPrinter {
    /** In bill; trả lỗi tiếng Việt nếu chưa kết nối / thất bại. */
    suspend fun print(data: ReceiptData): PrintResult
    fun savedPrinterMac(): String?
    fun savePrinterMac(mac: String)
}
```

- [ ] **Step 2:** `EscPosReceiptPrinter.kt` — bọc DantSu lib (chạy IO dispatcher), in theo `ReceiptLayout`. Nếu thư viện không in được tiếng Việt có dấu → fallback in bitmap (DantSu hỗ trợ `printFormattedTextAndCut` + có thể vẽ bitmap). Mã hoá lỗi sang message VN:
```kotlin
package com.mykiot.pos.core.hardware.printer

import android.content.Context
import com.dantsu.escposprinter.EscPosPrinter
import com.dantsu.escposprinter.connection.bluetooth.BluetoothConnection
import com.dantsu.escposprinter.connection.bluetooth.BluetoothPrintersConnections
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class EscPosReceiptPrinter @Inject constructor(
    @ApplicationContext private val context: Context,
) : ReceiptPrinter {

    private val prefs = context.getSharedPreferences("printer_prefs", Context.MODE_PRIVATE)

    override fun savedPrinterMac(): String? = prefs.getString(KEY_MAC, null)
    override fun savePrinterMac(mac: String) { prefs.edit().putString(KEY_MAC, mac).apply() }

    override suspend fun print(data: ReceiptData): PrintResult = withContext(Dispatchers.IO) {
        try {
            val connection: BluetoothConnection = resolveConnection()
                ?: return@withContext PrintResult.Error("Chưa kết nối máy in. Vui lòng chọn máy in trong Cài đặt.")
            // 58mm ~ 32 ký tự, ~203dpi, khổ giấy 48mm in được, nbChar = 32
            val printer = EscPosPrinter(connection, 203, 48f, 32)
            val text = ReceiptLayout.render(data, width = 32)
                .joinToString("\n") { escape(it) }
            printer.printFormattedTextAndCut(text)
            PrintResult.Ok
        } catch (e: Exception) {
            PrintResult.Error("In bill thất bại: ${e.message ?: "lỗi không xác định"}")
        }
    }

    private fun resolveConnection(): BluetoothConnection? {
        val mac = savedPrinterMac()
        val all = BluetoothPrintersConnections().list?.toList().orEmpty()
        return if (mac != null) all.firstOrNull { it.device.address == mac } ?: all.firstOrNull()
        else BluetoothPrintersConnections.selectFirstPaired()
    }

    // DantSu formatter dùng '[' cho lệnh; escape ký tự đặc biệt tối thiểu.
    private fun escape(s: String): String = s.replace("[", "(")

    private companion object { const val KEY_MAC = "printer_mac" }
}
```

- [ ] **Step 3:** `BarcodeScanner.kt` (interface) — chỉ là hợp đồng callback; impl là Composable CameraX:
```kotlin
package com.mykiot.pos.core.hardware.scanner

/** Kết quả quét: chuỗi barcode thô. */
fun interface OnBarcode { fun onScanned(code: String) }
```

- [ ] **Step 4:** `MlKitScannerScreen.kt` — Composable mở camera, dùng ML Kit phân tích, gọi `onScanned` 1 lần rồi đóng. (UI hardware — verify thủ công.)
```kotlin
package com.mykiot.pos.core.hardware.scanner

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.Executors

@Composable
fun MlKitScannerScreen(onScanned: (String) -> Unit, onClose: () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val analysisExecutor = remember { Executors.newSingleThreadExecutor() }
    val scanner = remember { BarcodeScanning.getClient() }
    var handled = remember { booleanArrayOf(false) }

    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> if (!granted) onClose() }

    LaunchedEffect(Unit) { permission.launch(android.Manifest.permission.CAMERA) }

    DisposableEffect(Unit) { onDispose { analysisExecutor.shutdown(); scanner.close() } }

    Box(Modifier.fillMaxSize()) {
        AndroidView(factory = { ctx ->
            val previewView = PreviewView(ctx)
            val providerFuture = ProcessCameraProvider.getInstance(ctx)
            providerFuture.addListener({
                val provider = providerFuture.get()
                val preview = Preview.Builder().build().also { it.setSurfaceProvider(previewView.surfaceProvider) }
                val analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
                analysis.setAnalyzer(analysisExecutor) { proxy ->
                    @Suppress("UnsafeOptInUsageError")
                    val media = proxy.image
                    if (media != null) {
                        val img = InputImage.fromMediaImage(media, proxy.imageInfo.rotationDegrees)
                        scanner.process(img)
                            .addOnSuccessListener { codes ->
                                val raw = codes.firstOrNull()?.rawValue
                                if (raw != null && !handled[0]) {
                                    handled[0] = true
                                    onScanned(raw)
                                }
                            }
                            .addOnCompleteListener { proxy.close() }
                    } else proxy.close()
                }
                provider.unbindAll()
                provider.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
            }, ContextCompat.getMainExecutor(ctx))
            previewView
        }, modifier = Modifier.fillMaxSize())
    }
}
```

- [ ] **Step 5:** `HidScanField.kt` — ô input ẩn luôn focus, hứng ký tự súng HID, gọi callback khi gặp Enter:
```kotlin
package com.mykiot.pos.core.hardware.scanner

import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.text.input.ImeAction

/**
 * Ô ẩn (kích thước 0) luôn giữ focus để hứng input từ súng quét HID.
 * Súng gửi chuỗi barcode + Enter → onScanned được gọi, rồi xoá buffer.
 */
@Composable
fun HidScanField(enabled: Boolean, onScanned: (String) -> Unit) {
    if (!enabled) return
    var buffer by remember { mutableStateOf("") }
    val focus = remember { FocusRequester() }
    LaunchedEffect(Unit) { focus.requestFocus() }
    BasicTextField(
        value = buffer,
        onValueChange = { buffer = it },
        modifier = Modifier.focusRequester(focus),
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
        keyboardActions = KeyboardActions(onDone = {
            val code = buffer.trim()
            buffer = ""
            if (code.isNotEmpty()) onScanned(code)
        }),
    )
}
```

- [ ] **Step 6:** Hilt provide printer — thêm module `core/hardware/HardwareModule.kt`:
```kotlin
package com.mykiot.pos.core.hardware

import com.mykiot.pos.core.hardware.printer.EscPosReceiptPrinter
import com.mykiot.pos.core.hardware.printer.ReceiptPrinter
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class HardwareModule {
    @Binds @Singleton
    abstract fun receiptPrinter(impl: EscPosReceiptPrinter): ReceiptPrinter
}
```
- [ ] **Step 7: Commit** `feat(android): hardware scanner (ML Kit + HID) + máy in ESC/POS`.

---

## Task 6: PosRepository + PosViewModel (TDD ViewModel)

**Files:** `feature/pos/data/PosRepository.kt`, `feature/pos/PosUiState.kt`, `feature/pos/PosViewModel.kt`; test `PosViewModelTest.kt`

- [ ] **Step 1:** `PosRepository.kt` — bọc API trả `ApiResult`, map DTO → domain:
```kotlin
package com.mykiot.pos.feature.pos.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CustomerApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.SalesApi
import com.mykiot.pos.core.network.dto.*
import com.mykiot.pos.feature.pos.cart.Cart
import com.mykiot.pos.feature.pos.cart.CartLine
import java.math.BigDecimal
import javax.inject.Inject

data class ScannedProduct(val line: CartLine)
data class CustomerLite(val id: Long, val name: String, val phone: String?)

class PosRepository @Inject constructor(
    private val productApi: ProductApi,
    private val customerApi: CustomerApi,
    private val salesApi: SalesApi,
    private val errorMapper: ErrorMapper,
) {
    suspend fun search(q: String): ApiResult<List<ProductBriefDto>> =
        runCatching { productApi.search(q).items }.fold(
            { ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    suspend fun byBarcode(code: String): ApiResult<ProductBriefDto> =
        runCatching { productApi.byBarcode(code) }.fold(
            { ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Tạo hoá đơn DRAFT rồi complete trong 1 lần (POS bán nhanh). */
    suspend fun checkout(
        cart: Cart, customerId: Long?, payments: List<PaymentInputDto>, allowDebt: Boolean,
    ): ApiResult<InvoiceDto> = runCatching {
        val draft = salesApi.create(
            InvoiceCreateDto(
                customerId = customerId,
                discountAmount = cart.invoiceDiscount.toPlainString(),
                items = cart.lines.map {
                    InvoiceItemInputDto(
                        productId = it.productId, unitId = it.unitId,
                        quantity = it.quantity.toPlainString(),
                        unitPrice = it.unitPrice.toPlainString(),
                        discountAmount = it.discount.toPlainString(),
                    )
                },
            ),
        )
        salesApi.complete(draft.id, InvoiceCompleteDto(payments = payments, allowDebt = allowDebt))
    }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    fun toCartLine(dto: ProductBriefDto): CartLine {
        val mu = dto.matchedUnit
        return if (mu != null) {
            CartLine(
                productId = dto.id, unitId = mu.id, name = dto.name, sku = dto.sku,
                unitName = mu.unitName,
                unitPrice = BigDecimal((mu.salePrice ?: dto.salePrice * mu.conversionRate).toString()),
                quantity = BigDecimal.ONE,
            )
        } else {
            CartLine(
                productId = dto.id, unitId = null, name = dto.name, sku = dto.sku,
                unitName = dto.unit, unitPrice = BigDecimal(dto.salePrice.toString()),
                quantity = BigDecimal.ONE,
            )
        }
    }
}
```

- [ ] **Step 2:** `PosUiState.kt`:
```kotlin
package com.mykiot.pos.feature.pos

import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.pos.cart.Cart
import com.mykiot.pos.feature.pos.data.CustomerLite

data class PosUiState(
    val cart: Cart = Cart(),
    val query: String = "",
    val searchResults: List<ProductBriefDto> = emptyList(),
    val customer: CustomerLite? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val lastInvoiceCode: String? = null,   // set sau khi checkout thành công → trigger in
)
```

- [ ] **Step 3: Test (fail)** `PosViewModelTest.kt`:
```kotlin
package com.mykiot.pos.feature.pos

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.pos.data.PosRepository
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import java.math.BigDecimal

@OptIn(ExperimentalCoroutinesApi::class)
class PosViewModelTest {

    private val repo: PosRepository = mockk(relaxed = true)
    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun brief(id: Long, price: Double) = ProductBriefDto(
        id = id, sku = "SKU$id", name = "SP$id", unit = "cái",
        salePrice = price, status = "ACTIVE",
    )

    private fun vm() = PosViewModel(repo).also {
        // dùng mapping thật của repo cho toCartLine
        coEvery { repo.toCartLine(any()) } answers { callOriginal() }
    }

    @Test fun `scanned barcode adds product to cart`() = runTest {
        coEvery { repo.byBarcode("8938505970", ) } returns ApiResult.Success(brief(1, 10000.0))
        val vm = PosViewModel(repo)
        coEvery { repo.toCartLine(any()) } answers { callOriginal() }

        vm.onBarcodeScanned("8938505970")

        val s = vm.state.value
        assertEquals(1, s.cart.lines.size)
        assertEquals(1L, s.cart.lines.first().productId)
    }

    @Test fun `scanning same barcode twice increments quantity`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1, 10000.0))
        val vm = PosViewModel(repo)
        coEvery { repo.toCartLine(any()) } answers { callOriginal() }

        vm.onBarcodeScanned("x"); vm.onBarcodeScanned("x")

        assertEquals(1, vm.state.value.cart.lines.size)
        assertEquals(BigDecimal("2"), vm.state.value.cart.lines.first().quantity)
    }

    @Test fun `unknown barcode surfaces vietnamese error, cart unchanged`() = runTest {
        coEvery { repo.byBarcode(any()) } returns
            ApiResult.Failure(com.mykiot.pos.core.network.ApiError("NOT_FOUND", "Không tìm thấy sản phẩm", 404))
        val vm = PosViewModel(repo)

        vm.onBarcodeScanned("nope")

        assertEquals(0, vm.state.value.cart.lines.size)
        assertEquals("Không tìm thấy sản phẩm", vm.state.value.errorMessage)
    }

    @Test fun `checkout success sets invoice code and clears cart`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1, 10000.0))
        coEvery { repo.toCartLine(any()) } answers { callOriginal() }
        coEvery { repo.checkout(any(), any(), any(), any()) } returns ApiResult.Success(
            InvoiceDto(
                id = 7, code = "HD20260609-007", subtotal = "10000", discountAmount = "0",
                total = "10000", paidAmount = "10000", changeAmount = "0", status = "COMPLETED",
                createdAt = "2026-06-09T14:00:00Z",
            ),
        )
        val vm = PosViewModel(repo)
        coEvery { repo.toCartLine(any()) } answers { callOriginal() }
        vm.onBarcodeScanned("x")

        vm.checkout(listOf(), allowDebt = false)   // payment list filled by dialog in UI

        val s = vm.state.value
        assertEquals("HD20260609-007", s.lastInvoiceCode)
        assertEquals(0, s.cart.lines.size)
        assertNull(s.errorMessage)
    }

    @Test fun `checkout failure keeps cart and shows error`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1, 10000.0))
        coEvery { repo.toCartLine(any()) } answers { callOriginal() }
        coEvery { repo.checkout(any(), any(), any(), any()) } returns
            ApiResult.Failure(com.mykiot.pos.core.network.ApiError("INSUFFICIENT_STOCK", "SP1 chỉ còn 0", 400))
        val vm = PosViewModel(repo)
        coEvery { repo.toCartLine(any()) } answers { callOriginal() }
        vm.onBarcodeScanned("x")

        vm.checkout(listOf(), allowDebt = false)

        assertEquals(1, vm.state.value.cart.lines.size)
        assertEquals("SP1 chỉ còn 0", vm.state.value.errorMessage)
        assertNull(vm.state.value.lastInvoiceCode)
    }
}
```

- [ ] **Step 4: Impl** `PosViewModel.kt`:
```kotlin
package com.mykiot.pos.feature.pos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.PaymentInputDto
import com.mykiot.pos.feature.pos.data.CustomerLite
import com.mykiot.pos.feature.pos.data.PosRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import javax.inject.Inject

@HiltViewModel
class PosViewModel @Inject constructor(
    private val repository: PosRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(PosUiState())
    val state: StateFlow<PosUiState> = _state.asStateFlow()

    fun onQueryChange(q: String) {
        _state.update { it.copy(query = q) }
        if (q.length >= 2) viewModelScope.launch {
            when (val r = repository.search(q)) {
                is ApiResult.Success -> _state.update { it.copy(searchResults = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        } else _state.update { it.copy(searchResults = emptyList()) }
    }

    /** Camera ML Kit hoặc súng HID đều gọi vào đây. */
    fun onBarcodeScanned(code: String) {
        viewModelScope.launch {
            when (val r = repository.byBarcode(code)) {
                is ApiResult.Success -> addToCart(r.data)
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun addFromSearch(dto: com.mykiot.pos.core.network.dto.ProductBriefDto) = addToCart(dto)

    private fun addToCart(dto: com.mykiot.pos.core.network.dto.ProductBriefDto) {
        val line = repository.toCartLine(dto)
        _state.update {
            it.copy(cart = it.cart.addScanned(line), errorMessage = null, query = "", searchResults = emptyList())
        }
    }

    fun setQuantity(index: Int, qty: BigDecimal) =
        _state.update { it.copy(cart = it.cart.setQuantity(index, qty)) }

    fun setUnitPrice(index: Int, price: BigDecimal) =
        _state.update { it.copy(cart = it.cart.setUnitPrice(index, price)) }

    fun setLineDiscount(index: Int, d: BigDecimal) =
        _state.update { it.copy(cart = it.cart.setLineDiscount(index, d)) }

    fun removeLine(index: Int) =
        _state.update { it.copy(cart = it.cart.removeLine(index)) }

    fun setCustomer(c: CustomerLite?) = _state.update { it.copy(customer = c) }

    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun consumeInvoiceCode() = _state.update { it.copy(lastInvoiceCode = null) }

    fun checkout(payments: List<PaymentInputDto>, allowDebt: Boolean) {
        val s = _state.value
        if (s.cart.isEmpty()) {
            _state.update { it.copy(errorMessage = "Giỏ hàng trống") }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.checkout(s.cart, s.customer?.id, payments, allowDebt)) {
                is ApiResult.Success -> _state.update {
                    it.copy(loading = false, cart = it.cart.clear(), customer = null, lastInvoiceCode = r.data.code)
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }
}
```

- [ ] **Step 5:** Run `PosViewModelTest` → PASS. **Commit** `feat(android): PosRepository + PosViewModel (TDD)`.

---

## Task 7: PosScreen + dialogs + gắn vào tab Bán

UI Compose (verify build + thủ công). Gồm: thanh tìm + nút camera, `HidScanField` ẩn, danh sách giỏ (`CartLineRow` sửa qty/giá/giảm/xoá), thanh tổng + nút "Thanh toán", `PaymentDialog` (đa phương thức, hiển thị tiền thối), `CustomerPickerDialog`, `DraftListSheet`. Sau checkout thành công (`lastInvoiceCode != null`) → gọi `ReceiptPrinter.print(...)` rồi `consumeInvoiceCode()`.

**Files:** `feature/pos/PosScreen.kt`, `CartLineRow.kt`, `PaymentDialog.kt`, `CustomerPickerDialog.kt`; sửa `HomeScaffold` để tab Bán render `PosScreen`.

- [ ] **Step 1–N:** Viết các Composable (xem file thực thi đã commit). Điểm chính:
  - `PosScreen(viewModel: PosViewModel = hiltViewModel(), printer: ...)`: thu thập state, hiển thị search results, cart, tổng tiền `formatVnd(cart.total())`.
  - Nút camera mở `MlKitScannerScreen` (overlay toàn màn), `onScanned` → `viewModel.onBarcodeScanned(code)`; xin quyền CAMERA qua accompanist.
  - `PaymentDialog`: nhập số tiền + chọn phương thức (CASH mặc định), hiển thị `Thối lại = changeFor(paid)`; nút Xác nhận → `viewModel.checkout(payments, allowDebt)`.
  - Lỗi: hiển thị Snackbar tiếng Việt từ `state.errorMessage` rồi `clearError()`.
  - In bill: `LaunchedEffect(state.lastInvoiceCode)` → build `ReceiptData` từ invoice trả về + tenant info → `printer.print()` → nếu `PrintResult.Error` hiển thị Snackbar, luôn `consumeInvoiceCode()`.
- [ ] **Step cuối: Commit** `feat(android): màn POS + thanh toán + in bill, gắn tab Bán`.

---

## Phase 2 — Definition of Done

- Unit tests JVM mới đều xanh: `MoneyTest`, `CartTest`, `ReceiptLayoutTest`, `PosViewModelTest`.
- App build (`assembleDebug`).
- Thủ công (thiết bị thật): quét camera + súng HID đẩy SP vào giỏ +1/+gộp; thanh toán tạo hoá đơn COMPLETED trên backend; in bill 58mm ra giấy (tiếng Việt đọc được, fallback bitmap nếu cần).
- Mọi thông báo lỗi tiếng Việt.

> Lưu ý kết nối thiết bị thật: ML Kit + ESC/POS + súng HID chỉ verify được trên máy có Android SDK + thiết bị. Các phần logic thuần (cart, layout, viewmodel) đã được TDD và là tuyến phòng thủ chính.
