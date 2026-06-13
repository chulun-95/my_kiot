# Android App — Hoàn thiện tính năng còn lại

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuẩn hóa search bar + build màn Sản phẩm, Hóa đơn, Trả hàng cho app Android POS.

**Architecture:** Mỗi feature gồm `UiState → Repository → ViewModel → Screen`, theo đúng pattern đã có trong codebase (CustomerListScreen/InventoryScreen). Tests dùng MockK + UnconfinedTestDispatcher theo pattern `InventoryViewModelTest`.

**Tech Stack:** Kotlin + Jetpack Compose + Hilt + Retrofit + kotlinx.serialization + MockK + coroutines-test

---

## File map

| File | Trạng thái | Mô tả |
|------|-----------|-------|
| `core/ui/Components.kt` | Sửa | AppSearchField: thêm `.height(56.dp)` |
| `core/util/Money.kt` | Sửa | Thêm `formatDateTime(isoString)` |
| `core/network/dto/ProductDtos.kt` | Sửa | Thêm `ProductListDto` |
| `core/network/dto/SalesDtos.kt` | Sửa | Thêm `completedAt` vào `InvoiceBriefDto`, thêm `InvoiceListDto`, `CancelInvoiceDto` |
| `core/network/ProductApi.kt` | Sửa | Thêm `list()` |
| `core/network/SalesApi.kt` | Sửa | Thêm `list()`, `cancel()` |
| `feature/product/ProductListUiState.kt` | Tạo mới | Data class state |
| `feature/product/data/ProductListRepository.kt` | Tạo mới | Gọi ProductApi |
| `feature/product/ProductListViewModel.kt` | Tạo mới | HiltViewModel |
| `feature/product/ProductListScreen.kt` | Tạo mới | Composable UI |
| `feature/invoice/InvoiceListUiState.kt` | Tạo mới | Data class state |
| `feature/invoice/data/InvoiceListRepository.kt` | Tạo mới | Gọi SalesApi |
| `feature/invoice/InvoiceListViewModel.kt` | Tạo mới | HiltViewModel |
| `feature/invoice/InvoiceListScreen.kt` | Tạo mới | Composable UI |
| `feature/invoice/ReturnsViewModel.kt` | Tạo mới | HiltViewModel, filter COMPLETED |
| `feature/invoice/ReturnsScreen.kt` | Tạo mới | Composable UI |
| `navigation/HomeNavHost.kt` | Sửa | Wire up 3 màn mới |
| `test/.../product/ProductListViewModelTest.kt` | Tạo mới | Unit tests |
| `test/.../invoice/InvoiceListViewModelTest.kt` | Tạo mới | Unit tests |
| `test/.../invoice/ReturnsViewModelTest.kt` | Tạo mới | Unit tests |

Tất cả file đều trong package `com.mykiot.pos.*`. Đường dẫn gốc:
`android/app/src/main/java/com/mykiot/pos/`
Test: `android/app/src/test/java/com/mykiot/pos/`

---

## Task 1: Search bar chuẩn hóa + formatDateTime

**Files:**
- Sửa: `core/ui/Components.kt` (dòng 45–68)
- Sửa: `core/util/Money.kt`

- [ ] **Bước 1: Sửa AppSearchField thêm chiều cao cố định**

Trong `core/ui/Components.kt`, tìm `OutlinedTextField(` trong hàm `AppSearchField` (dòng ~45), đổi dòng `modifier = modifier,` thành:

```kotlin
modifier = modifier.height(56.dp),
```

> `56.dp` = chiều cao chuẩn Material3 cho single-line TextField. Tất cả 4 màn đang dùng `AppSearchField` sẽ nhất quán mà không cần sửa từng màn.

- [ ] **Bước 2: Thêm formatDateTime vào Money.kt**

Thêm vào cuối file `core/util/Money.kt`:

```kotlin
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

private val DT_DISPLAY = DateTimeFormatter.ofPattern("dd/MM HH:mm")

/**
 * "2026-06-13T10:30:00+07:00" → "13/06 10:30"
 * Trả "" nếu chuỗi null hoặc không parse được.
 */
fun formatDateTime(isoString: String?): String = try {
    if (isoString == null) "" else OffsetDateTime.parse(isoString).format(DT_DISPLAY)
} catch (_: Exception) { "" }
```

- [ ] **Bước 3: Chạy test hiện có để đảm bảo không bị break**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.*" -q
```

Kết quả mong đợi: `BUILD SUCCESSFUL`

- [ ] **Bước 4: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/Components.kt \
        android/app/src/main/java/com/mykiot/pos/core/util/Money.kt
git commit -m "fix(android): chuẩn hóa AppSearchField 56dp + thêm formatDateTime"
```

---

## Task 2: Foundation — DTOs + API interfaces

**Files:**
- Sửa: `core/network/dto/ProductDtos.kt`
- Sửa: `core/network/dto/SalesDtos.kt`
- Sửa: `core/network/ProductApi.kt`
- Sửa: `core/network/SalesApi.kt`

- [ ] **Bước 1: Thêm ProductListDto vào ProductDtos.kt**

Thêm vào cuối file `core/network/dto/ProductDtos.kt`:

```kotlin
@Serializable
data class ProductListDto(
    val items: List<ProductBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,  // PaginationDto đã có ở InventoryDtos.kt, cùng package
)
```

- [ ] **Bước 2: Cập nhật SalesDtos.kt**

Trong `core/network/dto/SalesDtos.kt`, thêm field `completedAt` vào `InvoiceBriefDto` (đổi toàn bộ class):

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

Thêm vào cuối file `SalesDtos.kt`:

```kotlin
@Serializable
data class InvoiceListDto(
    val items: List<InvoiceBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

@Serializable
data class CancelInvoiceDto(val reason: String)
```

- [ ] **Bước 3: Thêm list() vào ProductApi.kt**

```kotlin
interface ProductApi {
    @GET("products/search") suspend fun search(@Query("q") q: String): ProductSearchDto
    @GET("products/barcode/{code}") suspend fun byBarcode(@Path("code") code: String): ProductBriefDto
    @POST("products") suspend fun create(@Body body: ProductCreateDto): ProductBriefDto

    @GET("products")
    suspend fun list(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): ProductListDto
}
```

- [ ] **Bước 4: Thêm list() và cancel() vào SalesApi.kt**

```kotlin
interface SalesApi {
    @POST("invoices") suspend fun create(@Body body: InvoiceCreateDto): InvoiceDto
    @GET("invoices/{id}") suspend fun get(@Path("id") id: Long): InvoiceDto
    @POST("invoices/{id}/complete") suspend fun complete(@Path("id") id: Long, @Body body: InvoiceCompleteDto): InvoiceDto
    @GET("invoices/drafts") suspend fun drafts(): InvoiceDraftListDto

    @GET("invoices")
    suspend fun list(
        @Query("status") status: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
    ): InvoiceListDto

    @POST("invoices/{id}/cancel")
    suspend fun cancel(@Path("id") id: Long, @Body body: CancelInvoiceDto): InvoiceDto
}
```

- [ ] **Bước 5: Compile check**

```bash
cd android && ./gradlew :app:compileDebugKotlin -q
```

Kết quả mong đợi: `BUILD SUCCESSFUL`

- [ ] **Bước 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/
git commit -m "feat(android): DTO ProductListDto, InvoiceListDto, CancelInvoiceDto + APIs"
```

---

## Task 3: Màn Sản phẩm

**Files:**
- Tạo: `feature/product/ProductListUiState.kt`
- Tạo: `feature/product/data/ProductListRepository.kt`
- Tạo: `feature/product/ProductListViewModel.kt`
- Tạo: `test/.../feature/product/ProductListViewModelTest.kt`
- Tạo: `feature/product/ProductListScreen.kt`

### 3a — UiState + Repository

- [ ] **Bước 1: Tạo ProductListUiState.kt**

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

- [ ] **Bước 2: Tạo ProductListRepository.kt**

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
        runCatching { productApi.list(search = search?.takeIf { it.isNotBlank() }).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

### 3b — ViewModel + Test

- [ ] **Bước 3: Viết test thất bại trước**

Tạo `test/.../feature/product/ProductListViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.product

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.product.data.ProductListRepository
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
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ProductListViewModelTest {
    private val repo: ProductListRepository = mockk(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun product(id: Long) = ProductBriefDto(
        id = id, sku = "SP$id", name = "Sản phẩm $id",
        unit = "cái", salePrice = 10000.0, status = "ACTIVE",
    )

    @Test fun `init triggers load and populates items`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(product(1), product(2)))
        val vm = ProductListViewModel(repo)
        assertEquals(2, vm.state.value.items.size)
        assertEquals(false, vm.state.value.loading)
    }

    @Test fun `load failure shows error message`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi mạng"))
        val vm = ProductListViewModel(repo)
        assertEquals("Lỗi mạng", vm.state.value.errorMessage)
    }

    @Test fun `clearError resets errorMessage`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi mạng"))
        val vm = ProductListViewModel(repo)
        vm.clearError()
        assertNull(vm.state.value.errorMessage)
    }
}
```

- [ ] **Bước 4: Chạy test — mong đợi FAIL vì ProductListViewModel chưa tồn tại**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.product.*" -q
```

Kết quả mong đợi: compile error `Unresolved reference: ProductListViewModel`

- [ ] **Bước 5: Tạo ProductListViewModel.kt**

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
            when (val r = repository.list(_state.value.query.takeIf { it.isNotBlank() })) {
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

- [ ] **Bước 6: Chạy test — mong đợi PASS**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.product.*" -q
```

Kết quả mong đợi: `BUILD SUCCESSFUL`, 3 tests passed.

### 3c — Screen

- [ ] **Bước 7: Tạo ProductListScreen.kt**

```kotlin
package com.mykiot.pos.feature.product

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.util.formatVnd
import com.mykiot.pos.feature.product.AddProductScreen

@Composable
fun ProductListScreen(
    onBack: () -> Unit,
    viewModel: ProductListViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var showAdd by remember { mutableStateOf(false) }

    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    if (showAdd) {
        AddProductScreen(
            onCreated = { _ -> showAdd = false; viewModel.load() },
            onCancel = { showAdd = false },
        )
        return
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = "Sản phẩm",
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAdd = true },
                shape = RoundedCornerShape(18.dp),
                containerColor = MaterialTheme.colorScheme.onSurface,
                contentColor = MaterialTheme.colorScheme.surface,
            ) {
                Icon(Icons.Filled.Add, contentDescription = "Thêm sản phẩm")
            }
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            AppSearchField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                placeholder = "Tìm theo tên / SKU",
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            if (state.items.isEmpty() && !state.loading) {
                Text(
                    state.errorMessage ?: "Chưa có sản phẩm",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
            }
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.items, key = { it.id }) { p ->
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 10.dp),
                    ) {
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(p.name, fontWeight = FontWeight.SemiBold, maxLines = 1, modifier = Modifier.weight(1f))
                                    if (p.status != "ACTIVE") {
                                        Spacer(Modifier.padding(start = 6.dp))
                                        MonoBadge("Ngừng bán", filled = false)
                                    }
                                }
                                Spacer(Modifier.height(2.dp))
                                Text(
                                    "${p.sku} • ${p.unit}",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Text(
                                formatVnd(p.salePrice.toLong()),
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                    }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading && state.items.isEmpty(), message = "Đang tải sản phẩm...")
}
```

- [ ] **Bước 8: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/product/ \
        android/app/src/test/java/com/mykiot/pos/feature/product/
git commit -m "feat(android): màn Danh sách Sản phẩm + tests"
```

---

## Task 4: Màn Hóa đơn

**Files:**
- Tạo: `feature/invoice/InvoiceListUiState.kt`
- Tạo: `feature/invoice/data/InvoiceListRepository.kt`
- Tạo: `feature/invoice/InvoiceListViewModel.kt`
- Tạo: `test/.../feature/invoice/InvoiceListViewModelTest.kt`
- Tạo: `feature/invoice/InvoiceListScreen.kt`

### 4a — UiState + Repository

- [ ] **Bước 1: Tạo InvoiceListUiState.kt**

```kotlin
package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.dto.InvoiceBriefDto

data class InvoiceListUiState(
    val loading: Boolean = false,
    val allItems: List<InvoiceBriefDto> = emptyList(),
    val filterStatus: String? = null,       // null = tất cả, "COMPLETED", "CANCELLED"
    val cancelingId: Long? = null,          // ID đang chờ confirm hủy
    val errorMessage: String? = null,
) {
    val items: List<InvoiceBriefDto>
        get() = if (filterStatus == null) allItems
                else allItems.filter { it.status == filterStatus }
}
```

- [ ] **Bước 2: Tạo InvoiceListRepository.kt**

```kotlin
package com.mykiot.pos.feature.invoice.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.SalesApi
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.CancelInvoiceDto
import javax.inject.Inject

open class InvoiceListRepository @Inject constructor(
    private val salesApi: SalesApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(status: String? = null): ApiResult<List<InvoiceBriefDto>> =
        runCatching { salesApi.list(status = status).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun cancel(id: Long, reason: String): ApiResult<InvoiceDto> =
        runCatching { salesApi.cancel(id, CancelInvoiceDto(reason)) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

### 4b — ViewModel + Test

- [ ] **Bước 3: Viết test thất bại trước**

Tạo `test/.../feature/invoice/InvoiceListViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceItemDto
import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
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
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class InvoiceListViewModelTest {
    private val repo: InvoiceListRepository = mockk(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun brief(id: Long, status: String = "COMPLETED") = InvoiceBriefDto(
        id = id, code = "HD2026-00$id", total = "100000", paidAmount = "100000",
        status = status, createdAt = "2026-06-13T10:00:00+07:00",
    )

    private fun invoiceDto(id: Long) = InvoiceDto(
        id = id, code = "HD2026-00$id", subtotal = "100000", discountAmount = "0",
        total = "100000", paidAmount = "100000", changeAmount = "0",
        status = "CANCELLED", createdAt = "2026-06-13T10:00:00+07:00",
    )

    @Test fun `load populates allItems`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1), brief(2)))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        assertEquals(2, vm.state.value.allItems.size)
        assertEquals(false, vm.state.value.loading)
    }

    @Test fun `filter by status filters items`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(
            listOf(brief(1, "COMPLETED"), brief(2, "CANCELLED")),
        )
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.setFilter("COMPLETED")
        assertEquals(1, vm.state.value.items.size)
        assertEquals("COMPLETED", vm.state.value.items.first().status)
    }

    @Test fun `cancelInvoice updates item status to CANCELLED`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1, "COMPLETED")))
        coEvery { repo.cancel(1L, any()) } returns ApiResult.Success(invoiceDto(1))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.cancelInvoice(1L, "Khách đổi ý")
        assertEquals("CANCELLED", vm.state.value.allItems.first().status)
        assertNull(vm.state.value.cancelingId)
    }

    @Test fun `load failure sets errorMessage`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi mạng"))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        assertEquals("Lỗi mạng", vm.state.value.errorMessage)
    }
}
```

- [ ] **Bước 4: Chạy test — mong đợi FAIL**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.invoice.InvoiceListViewModelTest" -q
```

Kết quả mong đợi: compile error `Unresolved reference: InvoiceListViewModel`

- [ ] **Bước 5: Tạo InvoiceListViewModel.kt**

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

    protected open val loadStatus: String? = null   // null = tất cả; "COMPLETED" cho Returns

    private val _state = MutableStateFlow(InvoiceListUiState())
    val state: StateFlow<InvoiceListUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.list(status = loadStatus)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, allItems = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun setFilter(status: String?) = _state.update { it.copy(filterStatus = status) }

    fun requestCancel(id: Long) = _state.update { it.copy(cancelingId = id) }
    fun dismissCancel() = _state.update { it.copy(cancelingId = null) }

    fun cancelInvoice(id: Long, reason: String) {
        viewModelScope.launch {
            when (val r = repository.cancel(id, reason)) {
                is ApiResult.Success -> _state.update { s ->
                    s.copy(
                        allItems = s.allItems.map { if (it.id == id) it.copy(status = "CANCELLED") else it },
                        cancelingId = null,
                    )
                }
                is ApiResult.Failure -> _state.update { it.copy(cancelingId = null, errorMessage = r.error.message) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
```

- [ ] **Bước 6: Chạy test — mong đợi PASS**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.invoice.InvoiceListViewModelTest" -q
```

Kết quả mong đợi: `BUILD SUCCESSFUL`, 4 tests passed.

### 4c — Screen

- [ ] **Bước 7: Tạo InvoiceListScreen.kt**

```kotlin
package com.mykiot.pos.feature.invoice

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
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
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

@Composable
fun InvoiceListScreen(
    onBack: () -> Unit,
    viewModel: InvoiceListViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    // Dialog xác nhận hủy hóa đơn
    state.cancelingId?.let { cancelId ->
        var reason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = viewModel::dismissCancel,
            title = { Text("Hủy hóa đơn") },
            text = {
                Column {
                    Text("Nhập lý do hủy:")
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = reason,
                        onValueChange = { reason = it },
                        placeholder = { Text("VD: Khách đổi ý") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    enabled = reason.isNotBlank(),
                    onClick = { viewModel.cancelInvoice(cancelId, reason) },
                ) { Text("Xác nhận hủy", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = viewModel::dismissCancel) { Text("Đóng") }
            },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(title = "Hóa đơn", onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp))
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            // Filter chips
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    FilterChip(selected = state.filterStatus == null, onClick = { viewModel.setFilter(null) }, label = { Text("Tất cả") })
                }
                item {
                    FilterChip(selected = state.filterStatus == "COMPLETED", onClick = { viewModel.setFilter("COMPLETED") }, label = { Text("Đã bán") })
                }
                item {
                    FilterChip(selected = state.filterStatus == "CANCELLED", onClick = { viewModel.setFilter("CANCELLED") }, label = { Text("Đã hủy") })
                }
            }
            Spacer(Modifier.height(8.dp))

            if (state.items.isEmpty() && !state.loading) {
                Text(
                    state.errorMessage ?: "Chưa có hóa đơn",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
            }
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.items, key = { it.id }) { inv ->
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 10.dp)
                            .clickable(enabled = inv.status == "COMPLETED") {
                                viewModel.requestCancel(inv.id)
                            },
                    ) {
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(inv.code, fontWeight = FontWeight.SemiBold, maxLines = 1)
                                Spacer(Modifier.height(2.dp))
                                Text(
                                    buildString {
                                        append(inv.customerName ?: "Khách lẻ")
                                        val dt = formatDateTime(inv.completedAt ?: inv.createdAt)
                                        if (dt.isNotBlank()) append(" · $dt")
                                    },
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text(formatVnd(inv.total), fontWeight = FontWeight.SemiBold)
                                Spacer(Modifier.height(4.dp))
                                MonoBadge(
                                    text = if (inv.status == "COMPLETED") "Đã bán" else "Đã hủy",
                                    filled = inv.status == "COMPLETED",
                                )
                            }
                        }
                    }
                }
            }
        }
    }
    LoadingDialog(visible = state.loading && state.allItems.isEmpty(), message = "Đang tải hóa đơn...")
}
```

- [ ] **Bước 8: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/ \
        android/app/src/test/java/com/mykiot/pos/feature/invoice/InvoiceListViewModelTest.kt
git commit -m "feat(android): màn Hóa đơn + InvoiceListViewModel + tests"
```

---

## Task 5: Màn Trả hàng

**Files:**
- Tạo: `feature/invoice/ReturnsViewModel.kt`
- Tạo: `test/.../feature/invoice/ReturnsViewModelTest.kt`
- Tạo: `feature/invoice/ReturnsScreen.kt`

### 5a — ViewModel + Test

- [ ] **Bước 1: Viết test thất bại trước**

Tạo `test/.../feature/invoice/ReturnsViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
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

    private fun brief(id: Long) = InvoiceBriefDto(
        id = id, code = "HD2026-00$id", total = "100000", paidAmount = "100000",
        status = "COMPLETED", createdAt = "2026-06-13T10:00:00+07:00",
    )

    @Test fun `load gọi list với status COMPLETED`() = runTest {
        coEvery { repo.list("COMPLETED") } returns ApiResult.Success(listOf(brief(1)))
        val vm = ReturnsViewModel(repo)
        vm.load()
        coVerify { repo.list("COMPLETED") }
        assertEquals(1, vm.state.value.allItems.size)
    }
}
```

- [ ] **Bước 2: Chạy test — mong đợi FAIL**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.invoice.ReturnsViewModelTest" -q
```

Kết quả mong đợi: compile error `Unresolved reference: ReturnsViewModel`

- [ ] **Bước 3: Tạo ReturnsViewModel.kt**

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

- [ ] **Bước 4: Chạy test — mong đợi PASS**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.invoice.ReturnsViewModelTest" -q
```

Kết quả mong đợi: `BUILD SUCCESSFUL`, 1 test passed.

### 5b — Screen

- [ ] **Bước 5: Tạo ReturnsScreen.kt**

```kotlin
package com.mykiot.pos.feature.invoice

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ReturnsScreen(
    onBack: () -> Unit,
    viewModel: ReturnsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    // Dialog xác nhận trả hàng
    state.cancelingId?.let { cancelId ->
        var reason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = viewModel::dismissCancel,
            title = { Text("Xác nhận trả hàng") },
            text = {
                Column {
                    Text("Xác nhận trả hàng? Tồn kho sẽ được cộng lại.")
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = reason,
                        onValueChange = { reason = it },
                        placeholder = { Text("Lý do trả hàng") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    enabled = reason.isNotBlank(),
                    onClick = { viewModel.cancelInvoice(cancelId, reason) },
                ) { Text("Trả hàng", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = viewModel::dismissCancel) { Text("Đóng") }
            },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(title = "Trả hàng", onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp))
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            if (state.allItems.isEmpty() && !state.loading) {
                Text(
                    "Chưa có hóa đơn nào để trả",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
            }
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.allItems, key = { it.id }) { inv ->
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 10.dp)
                            .clickable { viewModel.requestCancel(inv.id) },
                    ) {
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(inv.code, fontWeight = FontWeight.SemiBold, maxLines = 1)
                                Spacer(Modifier.height(2.dp))
                                Text(
                                    buildString {
                                        append(inv.customerName ?: "Khách lẻ")
                                        val dt = formatDateTime(inv.completedAt ?: inv.createdAt)
                                        if (dt.isNotBlank()) append(" · $dt")
                                    },
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text(formatVnd(inv.total), fontWeight = FontWeight.SemiBold)
                                Spacer(Modifier.height(4.dp))
                                MonoBadge("Trả hàng", filled = false)
                            }
                        }
                    }
                }
            }
        }
    }
    LoadingDialog(visible = state.loading && state.allItems.isEmpty(), message = "Đang tải...")
}
```

- [ ] **Bước 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/invoice/ReturnsViewModel.kt \
        android/app/src/main/java/com/mykiot/pos/feature/invoice/ReturnsScreen.kt \
        android/app/src/test/java/com/mykiot/pos/feature/invoice/ReturnsViewModelTest.kt
git commit -m "feat(android): màn Trả hàng + ReturnsViewModel + test"
```

---

## Task 6: Wire navigation

**Files:**
- Sửa: `navigation/HomeNavHost.kt`

- [ ] **Bước 1: Cập nhật HomeNavHost.kt**

Mở `navigation/HomeNavHost.kt`. Thêm các import mới ở đầu file (sau các import hiện có):

```kotlin
import com.mykiot.pos.feature.product.ProductListScreen
import com.mykiot.pos.feature.invoice.InvoiceListScreen
import com.mykiot.pos.feature.invoice.ReturnsScreen
```

Tìm 3 dòng PlaceholderScreen và thay thế:

**Tìm:**
```kotlin
composable(Routes.PRODUCTS) { PlaceholderScreen("Sản phẩm", onBack = { nav.popBackStack() }) }
composable(Routes.INVOICE_HISTORY) { PlaceholderScreen("Hóa đơn", onBack = { nav.popBackStack() }) }
composable(Routes.RETURNS) { PlaceholderScreen("Trả hàng", onBack = { nav.popBackStack() }) }
```

**Thay bằng:**
```kotlin
composable(Routes.PRODUCTS) {
    ProductListScreen(onBack = { nav.popBackStack() })
}
composable(Routes.INVOICE_HISTORY) {
    InvoiceListScreen(onBack = { nav.popBackStack() })
}
composable(Routes.RETURNS) {
    ReturnsScreen(onBack = { nav.popBackStack() })
}
```

- [ ] **Bước 2: Build toàn bộ**

```bash
cd android && ./gradlew :app:assembleDebug -q
```

Kết quả mong đợi: `BUILD SUCCESSFUL`

- [ ] **Bước 3: Chạy toàn bộ test**

```bash
cd android && ./gradlew :app:testDebugUnitTest -q
```

Kết quả mong đợi: `BUILD SUCCESSFUL`, tất cả test pass.

- [ ] **Bước 4: Commit cuối**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt
git commit -m "feat(android): wire navigation Sản phẩm + Hóa đơn + Trả hàng"
```

---

## Tóm tắt thứ tự thực hiện

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6
(fixes) → (DTOs) → (Products) → (Invoices) → (Returns) → (Nav)
```

Mỗi task có thể build + test độc lập. Task 6 (navigation) chỉ chạy sau khi cả 3 feature screen đã có.

---

## Lưu ý kỹ thuật

- `PaginationDto` dùng từ `InventoryDtos.kt` — cùng package `com.mykiot.pos.core.network.dto`, không cần import thêm.
- `InvoiceListViewModel` được khai báo `open` với `loadStatus: String? = null` để `ReturnsViewModel` override thành `"COMPLETED"`. Hilt hỗ trợ subclass của `@HiltViewModel`.
- Network error khi test trên thiết bị thật: `local.properties` đã có `BASE_URL_DEBUG=http://192.168.110.73:8000/api/v1/` — đảm bảo backend đang chạy ở IP đó.
