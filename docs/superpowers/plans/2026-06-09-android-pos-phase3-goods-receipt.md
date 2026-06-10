# Android POS — Phase 3: Nhập hàng (Goods Receipt)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development hoặc executing-plans. Steps dùng checkbox.

**Goal:** Màn nhập hàng: chọn NCC → quét/tìm SP thêm dòng (số lượng + giá vốn + đơn vị) → tạo phiếu nhập DRAFT rồi hoàn tất (backend tự cộng tồn + tính giá vốn bình quân).

**Architecture:** Tiếp nối Phase 1–2. Thêm `feature/receipt` (domain `ReceiptBasket` thuần Kotlin — TDD, `ReceiptRepository`, `ReceiptViewModel` — TDD, UI Compose), `SupplierApi`, `InventoryApi` (phần receipts). Dùng lại `ProductApi` (search/barcode) + scanner Phase 2. Online-only.

**Phụ thuộc backend:** `GET /suppliers`, `POST /goods-receipts`, `POST /goods-receipts/{id}/complete`, `GET /goods-receipts`, `GET /goods-receipts/{id}`.

---

## File Structure (Phase 3)

- `core/network/dto/InventoryDtos.kt` (goods-receipt + supplier DTOs)
- `core/network/SupplierApi.kt`, `core/network/InventoryApi.kt` (+ provide Hilt)
- `feature/receipt/basket/ReceiptLine.kt`, `ReceiptBasket.kt` (TDD)
- `feature/receipt/data/ReceiptRepository.kt`
- `feature/receipt/ReceiptUiState.kt`, `ReceiptViewModel.kt` (TDD)
- `feature/receipt/ReceiptScreen.kt`, `ReceiptLineRow.kt`, `SupplierPickerDialog.kt`, `AddReceiptItemDialog.kt`
- `navigation/HomeScaffold`: tab Nhập → `ReceiptScreen`
- Tests: `ReceiptBasketTest.kt`, `ReceiptViewModelTest.kt`

---

## Task 1: DTOs + APIs

- [ ] **Step 1:** `core/network/dto/InventoryDtos.kt`:
```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SupplierDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    @SerialName("total_debt") val totalDebt: Double = 0.0,
)

@Serializable
data class SupplierListDto(val items: List<SupplierDto> = emptyList())

@Serializable
data class GoodsReceiptItemInputDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("unit_id") val unitId: Long? = null,
    val quantity: String,
    @SerialName("cost_price") val costPrice: String,
)

@Serializable
data class GoodsReceiptCreateDto(
    @SerialName("supplier_id") val supplierId: Long? = null,
    val items: List<GoodsReceiptItemInputDto>,
    @SerialName("paid_amount") val paidAmount: String = "0",
    @SerialName("payment_method") val paymentMethod: String = "CASH",
    val note: String? = null,
)

@Serializable
data class GoodsReceiptItemDto(
    val id: Long,
    @SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String? = null,
    @SerialName("product_sku") val productSku: String? = null,
    @SerialName("unit_id") val unitId: Long? = null,
    @SerialName("unit_name") val unitName: String? = null,
    val quantity: String,
    @SerialName("cost_price") val costPrice: String,
    @SerialName("line_total") val lineTotal: String,
)

@Serializable
data class GoodsReceiptDto(
    val id: Long,
    val code: String,
    @SerialName("supplier_id") val supplierId: Long? = null,
    @SerialName("supplier_name") val supplierName: String? = null,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    val items: List<GoodsReceiptItemDto> = emptyList(),
)
```
- [ ] **Step 2:** `SupplierApi.kt`:
```kotlin
package com.mykiot.pos.core.network
import com.mykiot.pos.core.network.dto.SupplierListDto
import retrofit2.http.GET
import retrofit2.http.Query
interface SupplierApi {
    @GET("suppliers") suspend fun list(@Query("search") search: String? = null): SupplierListDto
}
```
- [ ] **Step 3:** `InventoryApi.kt` (Phase 3 phần receipts; Phase 4 bổ sung inventory):
```kotlin
package com.mykiot.pos.core.network
import com.mykiot.pos.core.network.dto.GoodsReceiptCreateDto
import com.mykiot.pos.core.network.dto.GoodsReceiptDto
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Path
interface InventoryApi {
    @POST("goods-receipts") suspend fun createReceipt(@Body body: GoodsReceiptCreateDto): GoodsReceiptDto
    @POST("goods-receipts/{id}/complete") suspend fun completeReceipt(@Path("id") id: Long): GoodsReceiptDto
}
```
- [ ] **Step 4:** Provide trong `NetworkModule`:
```kotlin
@Provides @Singleton fun supplierApi(retrofit: Retrofit): SupplierApi = retrofit.create(SupplierApi::class.java)
@Provides @Singleton fun inventoryApi(retrofit: Retrofit): InventoryApi = retrofit.create(InventoryApi::class.java)
```
- [ ] **Step 5: Commit** `feat(android): API suppliers + goods-receipts`.

---

## Task 2: ReceiptBasket domain (TDD)

Giống Cart nhưng dòng có `costPrice` thay vì giá bán; total = Σ(qty×cost).

- [ ] **Step 1: Test (fail)** `ReceiptBasketTest.kt`:
```kotlin
package com.mykiot.pos.feature.receipt.basket

import org.junit.Assert.assertEquals
import org.junit.Test
import java.math.BigDecimal

class ReceiptBasketTest {
    private fun line(pid: Long, qty: String, cost: String) =
        ReceiptLine(productId = pid, unitId = null, name = "SP$pid", sku = "SKU$pid",
            unitName = "cái", costPrice = BigDecimal(cost), quantity = BigDecimal(qty))

    @Test fun `add scanned appends qty 1`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000"))
        assertEquals(1, b.lines.size)
    }
    @Test fun `scan same product increments`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000")).addScanned(line(1, "1", "8000"))
        assertEquals(1, b.lines.size); assertEquals(BigDecimal("2"), b.lines.first().quantity)
    }
    @Test fun `setQuantity and setCost update line`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000"))
            .setQuantity(0, BigDecimal("10")).setCost(0, BigDecimal("7500"))
        assertEquals(BigDecimal("10"), b.lines[0].quantity)
        assertEquals(BigDecimal("7500"), b.lines[0].costPrice)
    }
    @Test fun `lineTotal and total`() {
        val b = ReceiptBasket().addScanned(line(1, "10", "8000")).addScanned(line(2, "2", "5000"))
        assertEquals(BigDecimal("80000"), b.lines[0].lineTotal())
        assertEquals(BigDecimal("90000"), b.total())
    }
    @Test fun `remove drops line`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000")).addScanned(line(2, "1", "5000")).removeLine(0)
        assertEquals(1, b.lines.size); assertEquals(2L, b.lines.first().productId)
    }
}
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Impl** `ReceiptLine.kt` + `ReceiptBasket.kt` (xem file thực thi). `lineTotal = costPrice×quantity`; `addScanned` gộp theo (productId, unitId).
- [ ] **Step 4:** Run → PASS. **Commit** `feat(android): domain phiếu nhập (TDD)`.

---

## Task 3: ReceiptRepository + ReceiptViewModel (TDD)

- [ ] **Step 1:** `ReceiptRepository.kt`: `suppliers(search)`, `search(q)`, `byBarcode(code)` (dùng ProductApi), `submit(basket, supplierId, paidAmount, paymentMethod)` = createReceipt → completeReceipt; `toReceiptLine(dto)`.
- [ ] **Step 2: Test (fail)** `ReceiptViewModelTest.kt` — quét thêm dòng; submit thành công xoá basket + set lastReceiptCode; submit lỗi giữ basket + báo lỗi VN; submit khi rỗng báo "Phiếu nhập trống".
- [ ] **Step 3: Impl** `ReceiptUiState.kt` + `ReceiptViewModel.kt` (tương tự PosViewModel).
- [ ] **Step 4:** Run → PASS. **Commit** `feat(android): ReceiptRepository + ReceiptViewModel (TDD)`.

---

## Task 4: UI + gắn tab Nhập

- [ ] Viết `ReceiptScreen` (chọn NCC, ô tìm + nút quét, danh sách dòng `ReceiptLineRow` sửa qty/cost/xoá, tổng tiền, nút "Hoàn tất nhập"), `SupplierPickerDialog`, `AddReceiptItemDialog` (nhập số lượng + giá vốn khi thêm thủ công). Gắn vào tab Nhập trong `HomeScaffold`.
- [ ] **Commit** `feat(android): màn Nhập hàng, gắn tab Nhập`.

---

## Phase 3 — Definition of Done
- Unit test xanh: `ReceiptBasketTest`, `ReceiptViewModelTest`.
- App build. Thủ công: tạo phiếu nhập → hoàn tất → tồn kho tăng đúng ở backend (kiểm qua tab Tồn ở Phase 4 hoặc web). Lỗi tiếng Việt.
