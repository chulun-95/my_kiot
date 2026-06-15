# Android Complete Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện 5 tính năng còn thiếu trong Android app: search bar height chuẩn, màn Sản phẩm, màn Hóa đơn, màn Trả hàng, và đầy đủ unit test cho mỗi ViewModel.

**Architecture:** Mỗi feature theo pattern: `XUiState → XRepository → XViewModel → XScreen`. Repositories là `open class` với `@Inject constructor` để mockable. ViewModels dùng `@HiltViewModel`. Inheritance cho ReturnsViewModel: kế thừa InvoiceListViewModel và override `loadStatus = "COMPLETED"`.

**Tech Stack:** Kotlin, Jetpack Compose, Hilt, Retrofit2, kotlinx.serialization, MockK, coroutines-test.

---

## File Map

**Sửa:**
- `core/ui/Components.kt` — AppSearchField thêm `.height(56.dp)`
- `core/util/Money.kt` — thêm `formatDateTime()`
- `core/network/dto/SalesDtos.kt` — thêm `completedAt` vào `InvoiceBriefDto`, thêm `InvoiceListDto`, `CancelInvoiceDto`
- `core/network/dto/ProductDtos.kt` — thêm `ProductListDto`
- `core/network/ProductApi.kt` — thêm `list()`
- `core/network/SalesApi.kt` — thêm `list()`, `cancel()`
- `navigation/HomeNavHost.kt` — wire 3 màn mới

**Tạo mới (source):**
- `feature/product/ProductListUiState.kt`
- `feature/product/data/ProductListRepository.kt`
- `feature/product/ProductListViewModel.kt`
- `feature/product/ProductListScreen.kt`
- `feature/invoice/InvoiceListUiState.kt`
- `feature/invoice/data/InvoiceListRepository.kt`
- `feature/invoice/InvoiceListViewModel.kt`
- `feature/invoice/InvoiceListScreen.kt`
- `feature/invoice/ReturnsViewModel.kt`
- `feature/invoice/ReturnsScreen.kt`

**Tạo mới (test):**
- `test/.../feature/product/ProductListViewModelTest.kt`
- `test/.../feature/invoice/InvoiceListViewModelTest.kt`
- `test/.../feature/invoice/ReturnsViewModelTest.kt`

---

## Task 1: Search bar — chuẩn hóa chiều cao 56dp

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/ui/Components.kt`

- [ ] **Step 1: Thêm `height` import và fix `AppSearchField`**

Trong `Components.kt`, thêm import và sửa modifier của `OutlinedTextField`:

Thêm dòng import (sau các import layout hiện có):
```
import androidx.compose.foundation.layout.height
```

Sửa dòng cuối của `OutlinedTextField` bên trong `AppSearchField`:
```kotlin
// Trước:
        modifier = modifier,
// Sau:
        modifier = modifier.height(56.dp),
```

- [ ] **Step 2: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/Components.kt
git commit -m "fix(android): chuẩn hóa search bar height 56dp trên mọi màn"
```

---

## Task 2: Foundation — helper date, DTOs, APIs

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/util/Money.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/dto/SalesDtos.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/dto/ProductDtos.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/ProductApi.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/SalesApi.kt`

- [ ] **Step 1: Thêm `formatDateTime()` vào cuối `Money.kt`**

```kotlin
/** "13/06 10:30" — ISO 8601 → múi giờ VN (+07:00). Trả "—" nếu null hoặc lỗi parse. */
fun formatDateTime(iso: String?): String {
    if (iso == null) return "—"
    return try {
        val dt = java.time.OffsetDateTime.parse(iso)
        val vn = dt.withOffsetSameInstant(java.time.ZoneOffset.ofHours(7))
        "%02d/%02d %02d:%02d".format(vn.dayOfMonth, vn.monthValue, vn.hour, vn.minute)
    } catch (_: Exception) {
        iso.take(10)
    }
}
```

- [ ] **Step 2: Cập nhật `SalesDtos.kt`**

Thêm field `completedAt` vào `InvoiceBriefDto` (có default null để backward-compatible):
```kotlin
@Serializable
data class InvoiceBriefDto(
    val id: Long,
    val code: String,
    @SerialName("customer_name") val customerName: String? = null,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
)
```

Append sau `InvoiceDraftListDto`:
```kotlin
@Serializable
data class InvoiceListDto(
    val items: List<InvoiceBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

@Serializable
data class CancelInvoiceDto(val reason: String)
```

*(PaginationDto đã có trong `InventoryDtos.kt`, cùng package `dto` — không cần import)*

- [ ] **Step 3: Thêm `ProductListDto` vào cuối `ProductDtos.kt`**

```kotlin
@Serializable
data class ProductListDto(
    val items: List<ProductBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)
```

- [ ] **Step 4: Ghi đè toàn bộ `ProductApi.kt`**

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.core.network.dto.ProductListDto
import com.mykiot.pos.core.network.dto.ProductSearchDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ProductApi {
    @GET("products")
    suspend fun list(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): ProductListDto

    @GET("products/search") suspend fun search(@Query("q") q: String): ProductSearchDto
    @GET("products/barcode/{code}") suspend fun byBarcode(@Path("code") code: String): ProductBriefDto
    @POST("products") suspend fun create(@Body body: ProductCreateDto): ProductBriefDto
}
```

- [ ] **Step 5: Ghi đè toàn bộ `SalesApi.kt`**

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CancelInvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceCompleteDto
import com.mykiot.pos.core.network.dto.InvoiceCreateDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceDraftListDto
import com.mykiot.pos.core.network.dto.InvoiceListDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface SalesApi {
    @POST("invoices") suspend fun create(@Body body: InvoiceCreateDto): InvoiceDto
    @GET("invoices/{id}") suspend fun get(@Path("id") id: Long): InvoiceDto
    @POST("invoices/{id}/complete") suspend fun complete(@Path("id") id: Long, @Body body: InvoiceCompleteDto): InvoiceDto
    @GET("invoices/drafts") suspend fun drafts(): InvoiceDraftListDto

    @GET("invoices")
    suspend fun list(
        @Query("status") status: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): InvoiceListDto

    @POST("invoices/{id}/cancel")
    suspend fun cancel(@Path("id") id: Long, @Body body: CancelInvoiceDto): InvoiceDto
}
```

- [ ] **Step 6: Commit foundation**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/
git commit -m "feat(android): DTOs + API cho Products list, Invoice history + cancel"
```

---

## Task 3: Màn Sản phẩm — TDD

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/product/ProductListUiState.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/product/data/ProductListRepository.kt`
- Create: `android/app/src/test/java/com/mykiot/pos/feature/product/ProductListViewModelTest.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/product/ProductListViewModel.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/product/ProductListScreen.kt`

- [ ] **Step 1: Tạo `ProductListUiState.kt`**

```kotlin
package com.mykiot.pos.feature.product

import com.mykiot.pos.core.network.dto.ProductBriefDto

data class ProductListUiState(
    val loading: Boolean = false,
    val items: List<ProductBriefDto> = emptyList(),
    val query: String = "",
    val errorMessage: String? = null,
)
```

- [ ] **Step 2: Tạo `data/ProductListRepository.kt`**

```kotlin
package com.mykiot.pos.feature.product.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.dto.ProductBriefDto
import javax.inject.Inject

open class ProductListRepository @Inject constructor(
    private val productApi: ProductApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?): ApiResult<List<ProductBriefDto>> =
        runCatching { productApi.list(search = search.takeIf { !it.isNullOrBlank() }).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

- [ ] **Step 3: Viết test (sẽ FAIL — ViewModel chưa tồn tại)**

Tạo `android/app/src/test/java/com/mykiot/pos/feature/product/ProductListViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.product

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.product.data.ProductListRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ProductListViewModelTest {

    private val repo: ProductListRepository = mockk(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun product(id: Long) = ProductBriefDto(
        id = id, sku = "SKU$id", name = "Sản phẩm $id",
        unit = "cái", salePrice = 10000.0, status = "ACTIVE",
    )

    @Test fun `load populates items on success`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Success(listOf(product(1), product(2)))
        val vm = ProductListViewModel(repo)
        assertEquals(2, vm.state.value.items.size)
        assertEquals("Sản phẩm 1", vm.state.value.items.first().name)
        assertFalse(vm.state.value.loading)
    }

    @Test fun `load sets errorMessage on failure`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Failure(ApiError("NET", "Lỗi mạng"))
        val vm = ProductListViewModel(repo)
        assertEquals("Lỗi mạng", vm.state.value.errorMessage)
        assertFalse(vm.state.value.loading)
    }

    @Test fun `onQueryChange with 2 chars calls repo with query`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(emptyList())
        val vm = ProductListViewModel(repo)
        vm.onQueryChange("SP")
        coVerify { repo.list("SP") }
    }

    @Test fun `onQueryChange blank calls repo with null`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(emptyList())
        val vm = ProductListViewModel(repo)
        vm.onQueryChange("")
        coVerify { repo.list(null) }
    }

    @Test fun `clearError removes errorMessage`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Failure(ApiError("NET", "Lỗi"))
        val vm = ProductListViewModel(repo)
        vm.clearError()
        assertNull(vm.state.value.errorMessage)
    }
}
```

- [ ] **Step 4: Chạy tests — xác nhận FAIL**

```bash
cd android && ./gradlew test --tests "com.mykiot.pos.feature.product.ProductListViewModelTest" -q 2>&1 | tail -5
```
Expected: compilation error — `ProductListViewModel` chưa tồn tại.

- [ ] **Step 5: Tạo `ProductListViewModel.kt`**

```kotlin
package com.mykiot.pos.feature.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.feature.product.data.ProductListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ProductListViewModel @Inject constructor(
    private val repository: ProductListRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ProductListUiState())
    val state: StateFlow<ProductListUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            val q = _state.value.query.takeIf { it.isNotBlank() }
            when (val r = repository.list(q)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, items = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun onQueryChange(q: String) {
        _state.update { it.copy(query = q) }
        if (q.isBlank() || q.length >= 2) load()
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
```

- [ ] **Step 6: Chạy tests — xác nhận PASS**

```bash
cd android && ./gradlew test --tests "com.mykiot.pos.feature.product.ProductListViewModelTest" -q 2>&1 | tail -5
```
Expected: `BUILD SUCCESSFUL` — 5 tests passed.

- [ ] **Step 7: Tạo `ProductListScreen.kt`**

```kotlin
package com.mykiot.pos.feature.product

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ProductListScreen(
    onBack: () -> Unit,
    viewModel: ProductListViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(title = "Sản phẩm", onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp))
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { /* Phase 2: navigate to AddProductScreen */ },
                shape = RoundedCornerShape(18.dp),
                containerColor = MaterialTheme.colorScheme.onSurface,
                contentColor = MaterialTheme.colorScheme.surface,
            ) {
                Icon(Icons.Filled.Add, contentDescription = "Thêm sản phẩm")
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            AppSearchField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                placeholder = "Tìm theo tên / SKU",
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            if (state.items.isEmpty() && !state.loading) {
                Text(
                    "Chưa có sản phẩm",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
            }
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.items, key = { it.id }) { p ->
                    ProductListCard(p)
                }
            }
        }
    }

    LoadingDialog(visible = state.loading && state.items.isEmpty(), message = "Đang tải sản phẩm...")
}

@Composable
private fun ProductListCard(product: ProductBriefDto) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp),
    ) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        product.name,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        modifier = Modifier.weight(1f),
                    )
                    if (product.status == "INACTIVE") {
                        Spacer(Modifier.width(6.dp))
                        MonoBadge("Ngừng", filled = false)
                    }
                }
                Spacer(Modifier.height(2.dp))
                Text(
                    "${product.sku} • ${product.unit} • ${formatVnd(product.salePrice.toLong())}",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
```

- [ ] **Step 8: Commit màn Sản phẩm**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/product/
git add android/app/src/test/java/com/mykiot/pos/feature/product/
git commit -m "feat(android): màn Danh sách Sản phẩm + UT (5 tests)"
```

---

## Task 4: Màn Hóa đơn — TDD

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListUiState.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/invoice/data/InvoiceListRepository.kt`
- Create: `android/app/src/test/java/com/mykiot/pos/feature/invoice/InvoiceListViewModelTest.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListViewModel.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListScreen.kt`

- [ ] **Step 1: Tạo `InvoiceListUiState.kt`**

```kotlin
package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.dto.InvoiceBriefDto

enum class InvoiceFilter { ALL, COMPLETED, CANCELLED }

fun InvoiceFilter.label() = when (this) {
    InvoiceFilter.ALL -> "Tất cả"
    InvoiceFilter.COMPLETED -> "Đã bán"
    InvoiceFilter.CANCELLED -> "Đã hủy"
}

data class InvoiceListUiState(
    val loading: Boolean = false,
    val items: List<InvoiceBriefDto> = emptyList(),
    val filter: InvoiceFilter = InvoiceFilter.ALL,
    val cancelingId: Long? = null,
    val errorMessage: String? = null,
) {
    val displayedItems: List<InvoiceBriefDto>
        get() = when (filter) {
            InvoiceFilter.ALL -> items
            InvoiceFilter.COMPLETED -> items.filter { it.status == "COMPLETED" }
            InvoiceFilter.CANCELLED -> items.filter { it.status == "CANCELLED" }
        }
}
```

- [ ] **Step 2: Tạo `data/InvoiceListRepository.kt`**

```kotlin
package com.mykiot.pos.feature.invoice.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.SalesApi
import com.mykiot.pos.core.network.dto.CancelInvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import javax.inject.Inject

open class InvoiceListRepository @Inject constructor(
    private val salesApi: SalesApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(status: String?): ApiResult<List<InvoiceBriefDto>> =
        runCatching { salesApi.list(status = status).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun cancel(id: Long, reason: String): ApiResult<InvoiceDto> =
        runCatching { salesApi.cancel(id, CancelInvoiceDto(reason)) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

- [ ] **Step 3: Viết test (sẽ FAIL)**

Tạo `android/app/src/test/java/com/mykiot/pos/feature/invoice/InvoiceListViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class InvoiceListViewModelTest {

    private val repo: InvoiceListRepository = mockk(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun brief(id: Long, status: String = "COMPLETED") = InvoiceBriefDto(
        id = id, code = "HD-00$id", total = "100000",
        paidAmount = "100000", status = status,
        createdAt = "2026-06-13T10:00:00+07:00",
    )

    private fun invoiceDto(id: Long) = InvoiceDto(
        id = id, code = "HD-00$id", subtotal = "100000",
        discountAmount = "0", total = "100000", paidAmount = "100000",
        changeAmount = "0", status = "CANCELLED",
        createdAt = "2026-06-13T10:00:00+07:00", items = emptyList(),
    )

    @Test fun `load passes null status to repo`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Success(emptyList())
        val vm = InvoiceListViewModel(repo)
        vm.load()
        coVerify { repo.list(null) }
    }

    @Test fun `load populates items on success`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1), brief(2)))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        assertEquals(2, vm.state.value.items.size)
        assertFalse(vm.state.value.loading)
    }

    @Test fun `load sets errorMessage on failure`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi mạng"))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        assertEquals("Lỗi mạng", vm.state.value.errorMessage)
    }

    @Test fun `setFilter ALL shows all items`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(
            listOf(brief(1, "COMPLETED"), brief(2, "CANCELLED")),
        )
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.setFilter(InvoiceFilter.ALL)
        assertEquals(2, vm.state.value.displayedItems.size)
    }

    @Test fun `setFilter COMPLETED shows only completed`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(
            listOf(brief(1, "COMPLETED"), brief(2, "CANCELLED")),
        )
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.setFilter(InvoiceFilter.COMPLETED)
        assertEquals(1, vm.state.value.displayedItems.size)
        assertEquals("COMPLETED", vm.state.value.displayedItems.first().status)
    }

    @Test fun `setFilter CANCELLED shows only cancelled`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(
            listOf(brief(1, "COMPLETED"), brief(2, "CANCELLED")),
        )
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.setFilter(InvoiceFilter.CANCELLED)
        assertEquals(1, vm.state.value.displayedItems.size)
        assertEquals("CANCELLED", vm.state.value.displayedItems.first().status)
    }

    @Test fun `requestCancel sets cancelingId`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(emptyList())
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.requestCancel(42L)
        assertEquals(42L, vm.state.value.cancelingId)
    }

    @Test fun `dismissCancel clears cancelingId`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(emptyList())
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.requestCancel(42L)
        vm.dismissCancel()
        assertNull(vm.state.value.cancelingId)
    }

    @Test fun `cancelInvoice on success updates item status to CANCELLED`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1), brief(2)))
        coEvery { repo.cancel(1L, "Sai hàng") } returns ApiResult.Success(invoiceDto(1))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.cancelInvoice(1L, "Sai hàng")
        assertEquals("CANCELLED", vm.state.value.items.first { it.id == 1L }.status)
        assertNull(vm.state.value.cancelingId)
    }

    @Test fun `cancelInvoice on failure shows error`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1)))
        coEvery { repo.cancel(1L, any()) } returns ApiResult.Failure(ApiError("FORBIDDEN", "Không có quyền"))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.cancelInvoice(1L, "test")
        assertEquals("Không có quyền", vm.state.value.errorMessage)
    }

    @Test fun `clearError removes errorMessage`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi"))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.clearError()
        assertNull(vm.state.value.errorMessage)
    }
}
```

- [ ] **Step 4: Chạy tests — xác nhận FAIL**

```bash
cd android && ./gradlew test --tests "com.mykiot.pos.feature.invoice.InvoiceListViewModelTest" -q 2>&1 | tail -5
```
Expected: compilation error.

- [ ] **Step 5: Tạo `InvoiceListViewModel.kt`**

```kotlin
package com.mykiot.pos.feature.invoice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
open class InvoiceListViewModel @Inject constructor(
    private val repository: InvoiceListRepository,
) : ViewModel() {

    protected open val loadStatus: String? = null

    private val _state = MutableStateFlow(InvoiceListUiState())
    val state: StateFlow<InvoiceListUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.list(status = loadStatus)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, items = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun setFilter(f: InvoiceFilter) = _state.update { it.copy(filter = f) }

    fun requestCancel(id: Long) = _state.update { it.copy(cancelingId = id) }

    fun dismissCancel() = _state.update { it.copy(cancelingId = null) }

    fun cancelInvoice(id: Long, reason: String) {
        _state.update { it.copy(cancelingId = null) }
        viewModelScope.launch {
            when (val r = repository.cancel(id, reason)) {
                is ApiResult.Success -> _state.update { s ->
                    s.copy(items = s.items.map { if (it.id == id) it.copy(status = "CANCELLED") else it })
                }
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
```

- [ ] **Step 6: Chạy tests — xác nhận PASS**

```bash
cd android && ./gradlew test --tests "com.mykiot.pos.feature.invoice.InvoiceListViewModelTest" -q 2>&1 | tail -5
```
Expected: `BUILD SUCCESSFUL` — 10 tests passed.

- [ ] **Step 7: Tạo `InvoiceListScreen.kt`**

```kotlin
package com.mykiot.pos.feature.invoice

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

@Composable
fun InvoiceListScreen(
    viewModel: InvoiceListViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    state.cancelingId?.let { cancelId ->
        var reason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = viewModel::dismissCancel,
            title = { Text("Hủy hóa đơn?") },
            text = {
                Column {
                    Text("Hủy sẽ hoàn lại tồn kho. Không thể hoàn tác.")
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = reason,
                        onValueChange = { reason = it },
                        label = { Text("Lý do hủy") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    enabled = reason.isNotBlank(),
                    onClick = { viewModel.cancelInvoice(cancelId, reason) },
                ) {
                    Text("Xác nhận", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.SemiBold)
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::dismissCancel) { Text("Đóng") }
            },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                InvoiceFilter.entries.forEach { f ->
                    FilterChip(
                        selected = state.filter == f,
                        onClick = { viewModel.setFilter(f) },
                        label = { Text(f.label()) },
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            if (state.displayedItems.isEmpty() && !state.loading) {
                Text(
                    "Chưa có hóa đơn",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
            }
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.displayedItems, key = { it.id }) { inv ->
                    InvoiceCard(invoice = inv, onCancel = { viewModel.requestCancel(inv.id) })
                }
            }
        }
    }

    LoadingDialog(visible = state.loading && state.items.isEmpty(), message = "Đang tải hóa đơn...")
}

@Composable
private fun InvoiceCard(invoice: InvoiceBriefDto, onCancel: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp),
    ) {
        Column(
            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(invoice.code, fontWeight = FontWeight.SemiBold)
                MonoBadge(
                    text = if (invoice.status == "COMPLETED") "Đã bán" else "Đã hủy",
                    filled = invoice.status == "COMPLETED",
                )
            }
            Spacer(Modifier.height(4.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    invoice.customerName ?: "Khách lẻ",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    formatDateTime(invoice.completedAt ?: invoice.createdAt),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.height(4.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(formatVnd(invoice.total), fontWeight = FontWeight.SemiBold)
                if (invoice.status == "COMPLETED") {
                    TextButton(onClick = onCancel) {
                        Text("Hủy", color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 8: Commit màn Hóa đơn**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListUiState.kt
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/data/InvoiceListRepository.kt
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListViewModel.kt
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/InvoiceListScreen.kt
git add android/app/src/test/java/com/mykiot/pos/feature/invoice/InvoiceListViewModelTest.kt
git commit -m "feat(android): màn Lịch sử Hóa đơn + filter + hủy HĐ + UT (10 tests)"
```

---

## Task 5: Màn Trả hàng — TDD

**Files:**
- Create: `android/app/src/test/java/com/mykiot/pos/feature/invoice/ReturnsViewModelTest.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/invoice/ReturnsViewModel.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/invoice/ReturnsScreen.kt`

- [ ] **Step 1: Viết test (sẽ FAIL)**

Tạo `android/app/src/test/java/com/mykiot/pos/feature/invoice/ReturnsViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ReturnsViewModelTest {

    private val repo: InvoiceListRepository = mockk(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun completedInvoice(id: Long) = InvoiceBriefDto(
        id = id, code = "HD-00$id", total = "100000",
        paidAmount = "100000", status = "COMPLETED",
        createdAt = "2026-06-13T10:00:00+07:00",
    )

    private fun cancelledDto(id: Long) = InvoiceDto(
        id = id, code = "HD-00$id", subtotal = "100000",
        discountAmount = "0", total = "100000", paidAmount = "100000",
        changeAmount = "0", status = "CANCELLED",
        createdAt = "2026-06-13T10:00:00+07:00", items = emptyList(),
    )

    @Test fun `load always passes COMPLETED status to repository`() = runTest {
        coEvery { repo.list("COMPLETED") } returns ApiResult.Success(emptyList())
        val vm = ReturnsViewModel(repo)
        vm.load()
        coVerify(exactly = 1) { repo.list("COMPLETED") }
    }

    @Test fun `load populates only COMPLETED invoices`() = runTest {
        coEvery { repo.list("COMPLETED") } returns ApiResult.Success(
            listOf(completedInvoice(1), completedInvoice(2)),
        )
        val vm = ReturnsViewModel(repo)
        vm.load()
        assertEquals(2, vm.state.value.items.size)
        assertEquals("COMPLETED", vm.state.value.items.first().status)
    }

    @Test fun `cancelInvoice updates item status to CANCELLED`() = runTest {
        coEvery { repo.list("COMPLETED") } returns ApiResult.Success(listOf(completedInvoice(1)))
        coEvery { repo.cancel(1L, "Khách đổi ý") } returns ApiResult.Success(cancelledDto(1))
        val vm = ReturnsViewModel(repo)
        vm.load()
        vm.cancelInvoice(1L, "Khách đổi ý")
        assertEquals("CANCELLED", vm.state.value.items.first().status)
    }
}
```

- [ ] **Step 2: Chạy test — xác nhận FAIL**

```bash
cd android && ./gradlew test --tests "com.mykiot.pos.feature.invoice.ReturnsViewModelTest" -q 2>&1 | tail -5
```
Expected: compilation error — `ReturnsViewModel` chưa tồn tại.

- [ ] **Step 3: Tạo `ReturnsViewModel.kt`**

```kotlin
package com.mykiot.pos.feature.invoice

import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class ReturnsViewModel @Inject constructor(
    repository: InvoiceListRepository,
) : InvoiceListViewModel(repository) {
    override val loadStatus: String = "COMPLETED"
}
```

- [ ] **Step 4: Chạy test — xác nhận PASS**

```bash
cd android && ./gradlew test --tests "com.mykiot.pos.feature.invoice.ReturnsViewModelTest" -q 2>&1 | tail -5
```
Expected: `BUILD SUCCESSFUL` — 3 tests passed.

- [ ] **Step 5: Tạo `ReturnsScreen.kt`**

```kotlin
package com.mykiot.pos.feature.invoice

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ReturnsScreen(
    viewModel: ReturnsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    state.cancelingId?.let { cancelId ->
        var reason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = viewModel::dismissCancel,
            title = { Text("Xác nhận trả hàng?") },
            text = {
                Column {
                    Text("Tồn kho sẽ được cộng lại. Không thể hoàn tác.")
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = reason,
                        onValueChange = { reason = it },
                        label = { Text("Lý do trả") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    enabled = reason.isNotBlank(),
                    onClick = { viewModel.cancelInvoice(cancelId, reason) },
                ) {
                    Text("Xác nhận trả", fontWeight = FontWeight.SemiBold)
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::dismissCancel) { Text("Hủy") }
            },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            if (state.items.isEmpty() && !state.loading) {
                Text(
                    "Chưa có hóa đơn nào có thể trả",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
            }
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.items, key = { it.id }) { inv ->
                    ReturnCard(invoice = inv, onReturn = { viewModel.requestCancel(inv.id) })
                }
            }
        }
    }

    LoadingDialog(visible = state.loading && state.items.isEmpty(), message = "Đang tải hóa đơn...")
}

@Composable
private fun ReturnCard(invoice: InvoiceBriefDto, onReturn: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp),
    ) {
        Column(
            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(invoice.code, fontWeight = FontWeight.SemiBold)
                Text(
                    formatDateTime(invoice.completedAt ?: invoice.createdAt),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.height(4.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(
                        invoice.customerName ?: "Khách lẻ",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(formatVnd(invoice.total), fontWeight = FontWeight.SemiBold)
                }
                TextButton(onClick = onReturn) {
                    Text("Trả hàng", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
```

- [ ] **Step 6: Commit màn Trả hàng**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/ReturnsViewModel.kt
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/ReturnsScreen.kt
git add android/app/src/test/java/com/mykiot/pos/feature/invoice/ReturnsViewModelTest.kt
git commit -m "feat(android): màn Trả hàng + UT (3 tests)"
```

---

## Task 6: Wire navigation

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt`

- [ ] **Step 1: Ghi đè toàn bộ `HomeNavHost.kt`**

```kotlin
package com.mykiot.pos.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.feature.customer.AddCustomerScreen
import com.mykiot.pos.feature.customer.CustomerDetailScreen
import com.mykiot.pos.feature.customer.CustomerListScreen
import com.mykiot.pos.feature.inventory.InventoryScreen
import com.mykiot.pos.feature.invoice.InvoiceListScreen
import com.mykiot.pos.feature.invoice.ReturnsScreen
import com.mykiot.pos.feature.pos.PosScreen
import com.mykiot.pos.feature.product.ProductListScreen
import com.mykiot.pos.feature.receipt.ReceiptScreen
import com.mykiot.pos.feature.report.ReportScreen

@Composable
fun HomeRoot(onLogout: () -> Unit) {
    var showPos by remember { mutableStateOf(false) }
    if (showPos) {
        BackHandler { showPos = false }
        PosScreen(onClose = { showPos = false })
        return
    }
    HomeNavHost(onOpenPos = { showPos = true }, onLogout = onLogout)
}

@Composable
private fun HomeNavHost(onOpenPos: () -> Unit, onLogout: () -> Unit) {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = Routes.HUB) {
        composable(Routes.HUB) {
            HubScreen(onNavigate = { nav.navigate(it) }, onOpenPos = onOpenPos, onLogout = onLogout)
        }
        composable(Routes.RECEIPT) {
            FeatureScaffold("Nhập hàng", onBack = { nav.popBackStack() }) { ReceiptScreen() }
        }
        composable(Routes.INVENTORY) {
            FeatureScaffold("Tồn kho", onBack = { nav.popBackStack() }) { InventoryScreen() }
        }
        composable(Routes.REPORT) {
            FeatureScaffold("Báo cáo", onBack = { nav.popBackStack() }) { ReportScreen() }
        }
        composable(Routes.CUSTOMERS) {
            CustomerListScreen(
                onBack = { nav.popBackStack() },
                onOpenDetail = { nav.navigate(Routes.customerDetail(it)) },
                onAdd = { nav.navigate(Routes.CUSTOMER_ADD) },
            )
        }
        composable(
            Routes.CUSTOMER_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { back ->
            CustomerDetailScreen(customerId = back.arguments?.getLong("id") ?: 0L, onBack = { nav.popBackStack() })
        }
        composable(Routes.CUSTOMER_ADD) {
            AddCustomerScreen(onCreated = { nav.popBackStack() }, onCancel = { nav.popBackStack() })
        }
        composable(Routes.PRODUCTS) {
            ProductListScreen(onBack = { nav.popBackStack() })
        }
        composable(Routes.INVOICE_HISTORY) {
            FeatureScaffold("Hóa đơn", onBack = { nav.popBackStack() }) { InvoiceListScreen() }
        }
        composable(Routes.RETURNS) {
            FeatureScaffold("Trả hàng", onBack = { nav.popBackStack() }) { ReturnsScreen() }
        }
        composable(Routes.CHANGE_PASSWORD) {
            PlaceholderScreen("Đổi mật khẩu", onBack = { nav.popBackStack() })
        }
    }
}

@Composable
private fun FeatureScaffold(title: String, onBack: () -> Unit, content: @Composable () -> Unit) {
    BackHandler(onBack = onBack)
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = { AppHeader(title = title, onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) { content() }
    }
}

@Composable
private fun PlaceholderScreen(title: String, onBack: () -> Unit) {
    FeatureScaffold(title, onBack) {
        Column(Modifier.fillMaxSize().padding(16.dp)) {
            Text("Màn '$title' (đang dựng)")
            Spacer(Modifier.height(12.dp))
            Button(onClick = onBack) { Text("Quay lại") }
        }
    }
}
```

- [ ] **Step 2: Build để kiểm tra compile**

```bash
cd android && ./gradlew assembleDebug 2>&1 | tail -10
```
Expected: `BUILD SUCCESSFUL`

- [ ] **Step 3: Chạy toàn bộ test suite**

```bash
cd android && ./gradlew test -q 2>&1 | tail -10
```
Expected: `BUILD SUCCESSFUL` — tất cả tests pass (18 tests mới + tests hiện có).

- [ ] **Step 4: Commit cuối**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt
git commit -m "feat(android): wire navigation — Sản phẩm, Hóa đơn, Trả hàng thay thế placeholder"
```

---

## Self-Review

- [x] **Spec coverage:** search bar ✅ | network (local.properties đã có IP đúng, không cần sửa) ✅ | Sản phẩm ✅ | Hóa đơn ✅ | Trả hàng Hướng A ✅
- [x] **Placeholders:** FAB AddProduct ghi chú "Phase 2" rõ ràng — không phải TBD vô định ✅
- [x] **Type consistency:** `InvoiceBriefDto.status` = `"CANCELLED"` / `"COMPLETED"` nhất quán trong VM, tests, screen ✅
- [x] **PaginationDto:** cùng package `dto` — không cần import thêm ✅
- [x] **`formatDateTime`:** export từ `core.util` package — import đúng ở 2 screens ✅
- [x] **Inheritance:** `InvoiceListViewModel` là `open class`, `protected open val loadStatus` — `ReturnsViewModel` override `"COMPLETED"` ✅
- [x] **18 unit tests mới:** 5 (Product) + 10 (InvoiceList) + 3 (Returns) ✅
