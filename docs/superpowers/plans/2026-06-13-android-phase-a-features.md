# Android — Hướng A (chức năng dùng chung 2 role) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung vào app android các màn dùng chung cho cả OWNER và CASHIER mà web đã có nhưng app còn thiếu: Khách hàng, Sản phẩm (DS/chi tiết/sửa), Hóa đơn (lịch sử/chi tiết), Trả hàng, Đổi mật khẩu — theo thứ tự ưu tiên.

**Architecture:** Giữ nguyên kiến trúc hiện có (Hilt DI, Retrofit + kotlinx.serialization, repository `open` + `ApiResult`, HiltViewModel + `StateFlow<UiState>`, Compose). Thêm **một nền tảng điều hướng nhẹ** (NavController trong Home) để mở list→detail→form mà không phá vỡ 3 tab + nút POS hiện tại. Mỗi feature là một vertical slice: Api → DTO → Repository → ViewModel → Screen → wire vào nav. Tests bám pattern hiện có: VM test bằng mockk fake repository + turbine + coroutines-test (UI Compose verify thủ công như phần còn lại của codebase).

**Tech Stack:** Kotlin, Jetpack Compose (Material3), Hilt, Retrofit, kotlinx.serialization, Navigation-Compose, JUnit4 + mockk + turbine + kotlinx-coroutines-test.

---

## Roadmap hướng A — thứ tự ưu tiên

| Phase | Nội dung | Trạng thái plan này |
|------|----------|---------------------|
| **0** | **Hub Home** (lưới card gom nhóm) + NavController để mở các màn; POS là nút lớn mở toàn màn | ✅ chi tiết đầy đủ dưới đây |
| **1** | **Khách hàng** — DS + tìm + chi tiết + tạo | ✅ chi tiết đầy đủ dưới đây |
| **2** | **Sản phẩm** — DS + tìm + chi tiết + sửa (tái dùng AddProduct) | 📋 spec ở cuối — bung plan riêng |
| **3** | **Hóa đơn** — lịch sử + chi tiết + in lại | 📋 spec ở cuối — bung plan riêng |
| **4** | **Trả hàng (returns)** — tạo từ hóa đơn + DS | 📋 spec ở cuối — bung plan riêng |
| **5** | **Đổi mật khẩu** | 📋 spec ở cuối — bung plan riêng |

> **Ghi chú phạm vi (Scope Check):** các nút **OWNER-only** nằm bên trong màn hướng A (Ngừng bán SP, Xóa KH, Hủy hóa đơn COMPLETED) **không** thuộc plan này — chúng phụ thuộc cơ chế RoleGate ở hướng B (lưu role vào session). Plan này chỉ làm phần read/create/edit dùng chung 2 role. Khi tới hướng B, các nút đó được thêm vào đúng màn đã dựng ở đây.

---

## File Structure (toàn hướng A)

```
core/network/
  CustomerApi.kt            # MỞ RỘNG: thêm get(id), create, update
  ProductApi.kt             # (Phase 2) MỞ RỘNG: list, get(id), update
  SalesApi.kt               # (Phase 3) MỞ RỘNG: list invoices, cancel
  ReturnApi.kt              # (Phase 4) TẠO MỚI
  AuthApi.kt                # (Phase 5) MỞ RỘNG: changePassword
  dto/CustomerDtos.kt       # MỞ RỘNG: detail + create + history
navigation/
  Routes.kt                 # MỞ RỘNG: route hub + 3 màn cũ + feature
  HomeRoot.kt               # TẠO MỚI: wrapper giữ overlay POS + bọc HomeNavHost
  HomeNavHost.kt            # TẠO MỚI: NavHost (start = Hub) + các destination
  HubScreen.kt              # TẠO MỚI: lưới card gom nhóm (điểm vào mọi chức năng)
  HomeScaffold.kt           # GỠ BỎ: thay bằng Hub + NavHost (không còn bottom-nav)
feature/customer/           # Phase 1 — TẠO MỚI
  CustomerListScreen.kt  CustomerListViewModel.kt  CustomerListUiState.kt
  CustomerDetailScreen.kt CustomerDetailViewModel.kt CustomerDetailUiState.kt
  AddCustomerScreen.kt   AddCustomerViewModel.kt
  data/CustomerRepository.kt
feature/product/            # Phase 2 — mở rộng thư mục đã có
feature/invoicehistory/     # Phase 3
feature/returns/            # Phase 4
feature/account/            # Phase 5 (ChangePasswordScreen)
```

---

## PHASE 0 — Hub Home + nền tảng điều hướng

**Vì sao cần:** Home hiện là 3 tab (Nhập/Tồn/Báo cáo) + nút POS, điều hướng bằng biến boolean, không có nav-stack để mở list→detail và không mở rộng được khi thêm chức năng. Thay bằng **Hub Home**: một màn lưới card gom nhóm, chạm card → mở màn trong qua `NavController`. **Bỏ bottom-nav.** POS giữ nguyên hành vi hiện tại: nút lớn → mở `PosScreen` toàn màn (overlay, ngoài nav-stack, để không phá luồng quét/in đang chạy). 3 màn cũ (Nhập/Tồn/Báo cáo) trở thành destination mở từ hub.

### Task 0.1: Thêm routes (hub + 3 màn cũ + feature)

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/Routes.kt`

- [ ] **Step 1: Thêm hằng route**

Thêm vào `object Routes` (giữ nguyên các hằng cũ `LOGIN`, `HOME`, `TAB_*`):

```kotlin
    // Home inner nav (NavController trong HomeNavHost)
    const val HUB = "hub"                  // màn lưới chức năng (start destination)
    const val RECEIPT = "receipt"          // Nhập hàng (màn cũ, nay là destination)
    const val INVENTORY = "inventory"      // Tồn kho
    const val REPORT = "report"            // Báo cáo
    const val CUSTOMERS = "customers"
    const val CUSTOMER_DETAIL = "customer_detail/{id}"  // arg: id
    const val CUSTOMER_ADD = "customer_add"
    const val PRODUCTS = "products"
    const val PRODUCT_DETAIL = "product_detail/{id}"
    const val INVOICE_HISTORY = "invoice_history"
    const val INVOICE_DETAIL = "invoice_detail/{id}"
    const val RETURNS = "returns"
    const val RETURN_NEW = "return_new"
    const val CHANGE_PASSWORD = "change_password"

    fun customerDetail(id: Long) = "customer_detail/$id"
    fun productDetail(id: Long) = "product_detail/$id"
    fun invoiceDetail(id: Long) = "invoice_detail/$id"
```

- [ ] **Step 2: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/Routes.kt
git commit -m "feat(android): route hub + màn cũ + feature hướng A"
```

### Task 0.2: Tạo HubScreen (lưới card gom nhóm)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt`

- [ ] **Step 1: Viết màn hub**

Bố cục: nút lớn **BÁN HÀNG (POS)** trên cùng (gọi `onOpenPos`), rồi các nhóm card (`LazyVerticalGrid` 2 cột) theo nghiệp vụ. Mỗi card chạm → `onNavigate(route)`. Header có nút Đăng xuất. **Chưa lọc role** ở phase này — mọi card hiện cho cả 2 role; hướng B sẽ thêm `visibleFor(role)` để ẩn card OWNER-only (đánh dấu `ownerOnly = true` sẵn để hướng B dùng).

```kotlin
package com.mykiot.pos.navigation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.AppHeader

private data class HubItem(
    val label: String,
    val route: String,
    val icon: ImageVector,
    val ownerOnly: Boolean = false,   // hướng B dùng để ẩn với CASHIER
)

private data class HubGroup(val title: String, val items: List<HubItem>)

private val hubGroups = listOf(
    HubGroup("Kho", listOf(
        HubItem("Nhập hàng", Routes.RECEIPT, Icons.Filled.Receipt),
        HubItem("Tồn kho", Routes.INVENTORY, Icons.Filled.Inventory2),
        HubItem("Trả hàng", Routes.RETURNS, Icons.Filled.AssignmentReturn),
    )),
    HubGroup("Danh mục", listOf(
        HubItem("Sản phẩm", Routes.PRODUCTS, Icons.Filled.Sell),
        HubItem("Khách hàng", Routes.CUSTOMERS, Icons.Filled.People),
    )),
    HubGroup("Bán hàng", listOf(
        HubItem("Hóa đơn", Routes.INVOICE_HISTORY, Icons.Filled.ReceiptLong),
    )),
    HubGroup("Báo cáo", listOf(
        HubItem("Tổng quan", Routes.REPORT, Icons.Filled.Assessment),
    )),
    HubGroup("Hệ thống", listOf(
        HubItem("Đổi mật khẩu", Routes.CHANGE_PASSWORD, Icons.Filled.Lock),
    )),
)

@Composable
fun HubScreen(
    onNavigate: (String) -> Unit,
    onOpenPos: () -> Unit,
    onLogout: () -> Unit,
) {
    Scaffold(
        topBar = {
            AppHeader(
                title = "my_kiot POS",
                modifier = Modifier.padding(horizontal = 16.dp),
                actions = { TextButton(onClick = onLogout) { Text("Đăng xuất") } },
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            // Nút POS lớn
            Surface(
                onClick = onOpenPos,
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.fillMaxWidth().height(72.dp),
            ) {
                Row(Modifier.fillMaxSize().padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.PointOfSale, contentDescription = null)
                    Spacer(Modifier.width(12.dp))
                    Text("BÁN HÀNG (POS)", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                }
            }
            Spacer(Modifier.height(16.dp))
            hubGroups.forEach { group ->
                Text(group.title, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    modifier = Modifier.fillMaxWidth().heightIn(max = 1000.dp),
                    userScrollEnabled = false,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(group.items, key = { it.route }) { item ->
                        HubCard(item, onClick = { onNavigate(item.route) })
                    }
                }
                Spacer(Modifier.height(16.dp))
            }
        }
    }
}

@Composable
private fun HubCard(item: HubItem, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surface,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth().height(88.dp),
    ) {
        Column(Modifier.fillMaxSize().padding(12.dp), verticalArrangement = Arrangement.Center) {
            Icon(item.icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(8.dp))
            Text(item.label, fontWeight = FontWeight.Medium)
        }
    }
}
```

> Lưu ý: nếu màn dài hơn 1 trang, bọc `Column` ngoài cùng bằng `verticalScroll(rememberScrollState())` (vì các `LazyVerticalGrid` con đã tắt scroll). Kiểm import icon `AssignmentReturn`/`Sell`/`People`/`ReceiptLong`/`Lock` có trong `material-icons-extended`; nếu artifact chỉ có core icons, thay bằng icon core sẵn có (vd `Icons.Filled.List`).

- [ ] **Step 2: Build**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL (có thể lỗi thiếu icon extended → xử lý theo lưu ý trên).

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt
git commit -m "feat(android): HubScreen — lưới chức năng gom nhóm"
```

### Task 0.3: HomeRoot + HomeNavHost

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt`

- [ ] **Step 1: Viết HomeRoot (giữ overlay POS) + HomeNavHost (NavHost)**

`HomeRoot` giữ state `showPos`. Nếu `showPos` → render `PosScreen(onClose=...)` toàn màn (BackHandler đóng), ngược lại render `HomeNavHost`. `HomeNavHost` start = `HUB`; hub gọi `onOpenPos` để bật overlay. 3 màn cũ bọc trong `FeatureScaffold` (AppHeader + back). Feature hướng A để **placeholder** tới khi phase tương ứng thay.

```kotlin
package com.mykiot.pos.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.feature.inventory.InventoryScreen
import com.mykiot.pos.feature.pos.PosScreen
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
        // ----- Feature hướng A: placeholder, thay ở từng phase -----
        composable(Routes.CUSTOMERS) { PlaceholderScreen("Khách hàng", onBack = { nav.popBackStack() }) }
        composable(
            Routes.CUSTOMER_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { PlaceholderScreen("Chi tiết KH", onBack = { nav.popBackStack() }) }
        composable(Routes.CUSTOMER_ADD) { PlaceholderScreen("Thêm KH", onBack = { nav.popBackStack() }) }
        composable(Routes.PRODUCTS) { PlaceholderScreen("Sản phẩm", onBack = { nav.popBackStack() }) }
        composable(Routes.INVOICE_HISTORY) { PlaceholderScreen("Hóa đơn", onBack = { nav.popBackStack() }) }
        composable(Routes.RETURNS) { PlaceholderScreen("Trả hàng", onBack = { nav.popBackStack() }) }
        composable(Routes.CHANGE_PASSWORD) { PlaceholderScreen("Đổi mật khẩu", onBack = { nav.popBackStack() }) }
    }
}

@Composable
private fun FeatureScaffold(title: String, onBack: () -> Unit, content: @Composable () -> Unit) {
    BackHandler(onBack = onBack)
    Scaffold(
        topBar = { AppHeader(title = title, onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
        containerColor = MaterialTheme.colorScheme.background,
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

> Cần `AppHeader` có tham số `onBack`. Mở `core/ui/Components.kt` xác nhận; nếu chưa có, thêm overload `AppHeader(title, onBack: (() -> Unit)? = null, actions, modifier)` render `IconButton` ArrowBack ở đầu — đồng bộ với cách `FormTopBar` trong `AddSupplierScreen` đang làm.

- [ ] **Step 2: Build**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt
git commit -m "feat(android): HomeRoot + HomeNavHost (hub + overlay POS + destination màn cũ)"
```

### Task 0.4: Thay HomeScaffold bằng HomeRoot

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/AppNav.kt`
- Delete: `android/app/src/main/java/com/mykiot/pos/navigation/HomeScaffold.kt`

- [ ] **Step 1: AppNav gọi HomeRoot**

Trong `AppNav.kt`, nhánh `composable(Routes.HOME)` gọi `HomeRoot` thay cho `HomeScaffold`:

```kotlin
        composable(Routes.HOME) {
            HomeRoot(
                onLogout = {
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(Routes.HOME) { inclusive = true }
                    }
                },
            )
        }
```

- [ ] **Step 2: Xóa HomeScaffold.kt**

`HomeScaffold` không còn được dùng (logic POS overlay đã chuyển sang `HomeRoot`, render màn cũ chuyển sang destination).

```bash
git rm android/app/src/main/java/com/mykiot/pos/navigation/HomeScaffold.kt
```

- [ ] **Step 3: Build + chạy app, verify thủ công**

Run: `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL. Mở app → thấy **Hub** với nút BÁN HÀNG lớn + các nhóm card. Bấm "BÁN HÀNG" → POS toàn màn, back về hub. Bấm "Nhập hàng"/"Tồn kho"/"Báo cáo" → mở màn cũ có nút back. Bấm "Khách hàng" → placeholder + nút Quay lại.

- [ ] **Step 4: Chạy unit test (đảm bảo không vỡ test cũ)**

Run: `./gradlew :app:testDebugUnitTest`
Expected: PASS toàn bộ test hiện có.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/AppNav.kt
git commit -m "feat(android): Hub Home thay bottom-nav (HomeRoot), gỡ HomeScaffold"
```

---

## PHASE 1 — Khách hàng (DS + tìm + chi tiết + tạo)

**Endpoints backend dùng:** `GET /customers?search=`, `GET /customers/{id}` (chi tiết + lịch sử mua), `POST /customers`, `GET /customers/phone/{phone}` (đã có). Tạo KH cần các field: name (bắt buộc), phone, email, address, note.

### Task 1.1: Mở rộng CustomerDtos

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/dto/CustomerDtos.kt`

- [ ] **Step 1: Thêm DTO chi tiết, tạo, lịch sử**

Giữ `CustomerDto` + `CustomerListDto` cũ. Thêm:

```kotlin
@Serializable
data class CustomerDetailDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    val note: String? = null,
    @SerialName("total_spent") val totalSpent: Double = 0.0,
    @SerialName("total_orders") val totalOrders: Int = 0,
    @SerialName("last_order_at") val lastOrderAt: String? = null,
    val history: List<CustomerHistoryItemDto> = emptyList(),
)

@Serializable
data class CustomerHistoryItemDto(
    val id: Long,
    val code: String,
    val total: Double = 0.0,
    @SerialName("completed_at") val completedAt: String? = null,
)

@Serializable
data class CustomerCreateDto(
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    val note: String? = null,
)
```

> Lưu ý: `Json { ignoreUnknownKeys = true }` đã bật trong NetworkModule → field thừa từ backend không gây lỗi. Nếu `GET /customers/{id}` không trả `history`, default `emptyList()` an toàn.

- [ ] **Step 2: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/dto/CustomerDtos.kt
git commit -m "feat(android): DTO chi tiết/tạo/lịch sử khách hàng"
```

### Task 1.2: Mở rộng CustomerApi

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/CustomerApi.kt`

- [ ] **Step 1: Thêm endpoint**

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.core.network.dto.CustomerListDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface CustomerApi {
    @GET("customers") suspend fun list(@Query("search") search: String? = null): CustomerListDto
    @GET("customers/phone/{phone}") suspend fun byPhone(@Path("phone") phone: String): CustomerDto
    @GET("customers/{id}") suspend fun get(@Path("id") id: Long): CustomerDetailDto
    @POST("customers") suspend fun create(@Body body: CustomerCreateDto): CustomerDetailDto
}
```

> `customerApi` provider trong `NetworkModule` đã có sẵn — không cần thêm DI.

- [ ] **Step 2: Build**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/CustomerApi.kt
git commit -m "feat(android): CustomerApi thêm get/create"
```

### Task 1.3: CustomerRepository

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/data/CustomerRepository.kt`

- [ ] **Step 1: Viết repository theo pattern InventoryRepository (open + runCatching.fold)**

```kotlin
package com.mykiot.pos.feature.customer.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CustomerApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.core.network.dto.CustomerDto
import javax.inject.Inject

open class CustomerRepository @Inject constructor(
    private val customerApi: CustomerApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?): ApiResult<List<CustomerDto>> =
        runCatching { customerApi.list(search = search).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun get(id: Long): ApiResult<CustomerDetailDto> =
        runCatching { customerApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(body: CustomerCreateDto): ApiResult<CustomerDetailDto> =
        runCatching { customerApi.create(body) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

- [ ] **Step 2: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/data/CustomerRepository.kt
git commit -m "feat(android): CustomerRepository"
```

### Task 1.4: CustomerListViewModel (TDD)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListUiState.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListViewModel.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/feature/customer/CustomerListViewModelTest.kt`

- [ ] **Step 1: Viết UiState**

```kotlin
package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.dto.CustomerDto

data class CustomerListUiState(
    val query: String = "",
    val items: List<CustomerDto> = emptyList(),
    val loading: Boolean = false,
    val errorMessage: String? = null,
)
```

- [ ] **Step 2: Viết test thất bại (bám InventoryViewModelTest)**

Tham khảo style: mockk `mockk<CustomerRepository>()`, `coEvery`, `Dispatchers.setMain`, turbine không bắt buộc (InventoryViewModelTest dùng assert trực tiếp trên `state.value`). Viết:

```kotlin
package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.feature.customer.data.CustomerRepository
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class CustomerListViewModelTest {
    private val repo = mockk<CustomerRepository>()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load populates items on success`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Success(
            listOf(CustomerDto(id = 1, name = "Anh Ba", phone = "0900000000")),
        )
        val vm = CustomerListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(1, vm.state.value.items.size)
        assertEquals("Anh Ba", vm.state.value.items.first().name)
    }

    @Test
    fun `load sets errorMessage on failure`() = runTest {
        coEvery { repo.list(null) } returns
            ApiResult.Failure(com.mykiot.pos.core.network.ApiError("X", "Lỗi tải"))
        val vm = CustomerListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals("Lỗi tải", vm.state.value.errorMessage)
    }
}
```

- [ ] **Step 3: Chạy test → FAIL**

Run: `./gradlew :app:testDebugUnitTest --tests "*CustomerListViewModelTest*"`
Expected: FAIL — `CustomerListViewModel` chưa tồn tại (unresolved reference).

- [ ] **Step 4: Viết ViewModel (bám InventoryViewModel)**

```kotlin
package com.mykiot.pos.feature.customer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.feature.customer.data.CustomerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CustomerListViewModel @Inject constructor(
    private val repository: CustomerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CustomerListUiState())
    val state: StateFlow<CustomerListUiState> = _state.asStateFlow()

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

- [ ] **Step 5: Chạy test → PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "*CustomerListViewModelTest*"`
Expected: PASS (2 test).

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListUiState.kt \
        android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListViewModel.kt \
        android/app/src/test/java/com/mykiot/pos/feature/customer/CustomerListViewModelTest.kt
git commit -m "feat(android): CustomerListViewModel + test"
```

### Task 1.5: CustomerListScreen

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListScreen.kt`

- [ ] **Step 1: Viết màn DS (header + ô tìm + danh sách, item bấm mở detail, FAB thêm)**

Dùng `AppHeader`, `AppTextField` (đã có trong `core/ui/Components.kt`), `collectAsStateWithLifecycle`, `hiltViewModel`. Item hiển thị tên + SĐT + tổng chi tiêu (format bằng `formatVnd` trong `core/util/Money.kt`).

```kotlin
package com.mykiot.pos.feature.customer

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.util.formatVnd

@Composable
fun CustomerListScreen(
    onBack: () -> Unit,
    onOpenDetail: (Long) -> Unit,
    onAdd: () -> Unit,
    viewModel: CustomerListViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        topBar = { AppHeader(title = "Khách hàng", onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
        floatingActionButton = {
            FloatingActionButton(onClick = onAdd) { Icon(Icons.Filled.Add, contentDescription = "Thêm") }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            AppTextField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                label = "Tìm theo tên / SĐT",
            )
            Spacer(Modifier.height(8.dp))
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.items, key = { it.id }) { c ->
                    Column(
                        Modifier.fillMaxWidth().clickable { onOpenDetail(c.id) }.padding(vertical = 12.dp),
                    ) {
                        Text(c.name, fontWeight = FontWeight.SemiBold)
                        Text(
                            buildString {
                                append(c.phone ?: "—")
                                append(" · ")
                                append(formatVnd(c.totalSpent.toString()))
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    HorizontalDivider()
                }
            }
        }
    }
}
```

> Trước khi viết: mở `core/ui/Components.kt` xác nhận chữ ký `AppHeader(title, onBack?, actions?, modifier)` và `AppTextField(value, onValueChange, label, ...)`. Nếu `AppHeader` chưa có tham số `onBack`, thêm nút back ở `actions` hoặc bổ sung overload — giữ đồng nhất với cách `FormTopBar` trong AddSupplierScreen làm.

- [ ] **Step 2: Build**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerListScreen.kt
git commit -m "feat(android): CustomerListScreen"
```

### Task 1.6: CustomerDetailViewModel (TDD)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerDetailUiState.kt`
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerDetailViewModel.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/feature/customer/CustomerDetailViewModelTest.kt`

- [ ] **Step 1: UiState**

```kotlin
package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.dto.CustomerDetailDto

data class CustomerDetailUiState(
    val customer: CustomerDetailDto? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
)
```

- [ ] **Step 2: Test thất bại**

```kotlin
package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.feature.customer.data.CustomerRepository
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class CustomerDetailViewModelTest {
    private val repo = mockk<CustomerRepository>()
    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load fetches customer by id`() = runTest {
        coEvery { repo.get(7) } returns ApiResult.Success(
            CustomerDetailDto(id = 7, name = "Chị Tư", phone = "0911111111"),
        )
        val vm = CustomerDetailViewModel(repo)
        vm.load(7)
        testScheduler.advanceUntilIdle()
        assertEquals("Chị Tư", vm.state.value.customer?.name)
    }
}
```

- [ ] **Step 3: Chạy → FAIL**

Run: `./gradlew :app:testDebugUnitTest --tests "*CustomerDetailViewModelTest*"`
Expected: FAIL — chưa có class.

- [ ] **Step 4: ViewModel**

```kotlin
package com.mykiot.pos.feature.customer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.feature.customer.data.CustomerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CustomerDetailViewModel @Inject constructor(
    private val repository: CustomerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CustomerDetailUiState())
    val state: StateFlow<CustomerDetailUiState> = _state.asStateFlow()

    fun load(id: Long) {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.get(id)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, customer = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
```

- [ ] **Step 5: Chạy → PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "*CustomerDetailViewModelTest*"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerDetailUiState.kt \
        android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerDetailViewModel.kt \
        android/app/src/test/java/com/mykiot/pos/feature/customer/CustomerDetailViewModelTest.kt
git commit -m "feat(android): CustomerDetailViewModel + test"
```

### Task 1.7: CustomerDetailScreen

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerDetailScreen.kt`

- [ ] **Step 1: Viết màn chi tiết (thông tin KH + thống kê + lịch sử mua)**

Header có nút back. Hiển thị name, phone, email, address, note, total_spent, total_orders, và `LazyColumn` lịch sử (`history`: code + total + completed_at). KHÔNG có nút "Xóa" (OWNER-only — để hướng B).

```kotlin
package com.mykiot.pos.feature.customer

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.util.formatVnd

@Composable
fun CustomerDetailScreen(
    customerId: Long,
    onBack: () -> Unit,
    viewModel: CustomerDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(customerId) { viewModel.load(customerId) }

    Scaffold(
        topBar = { AppHeader(title = state.customer?.name ?: "Khách hàng", onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
    ) { padding ->
        val c = state.customer
        Column(Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            if (c == null) {
                Text(state.errorMessage ?: "Đang tải...")
            } else {
                Text("SĐT: ${c.phone ?: "—"}")
                c.email?.let { Text("Email: $it") }
                c.address?.let { Text("Địa chỉ: $it") }
                c.note?.let { Text("Ghi chú: $it") }
                Spacer(Modifier.height(8.dp))
                Text("Tổng chi tiêu: ${formatVnd(c.totalSpent.toString())} · ${c.totalOrders} đơn", fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(12.dp))
                Text("Lịch sử mua", fontWeight = FontWeight.SemiBold)
                LazyColumn(Modifier.fillMaxWidth()) {
                    items(c.history, key = { it.id }) { h ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(h.code)
                            Text(formatVnd(h.total.toString()))
                        }
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 2: Build**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/CustomerDetailScreen.kt
git commit -m "feat(android): CustomerDetailScreen"
```

### Task 1.8: AddCustomerViewModel (TDD)

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/AddCustomerViewModel.kt`
- Test: `android/app/src/test/java/com/mykiot/pos/feature/customer/AddCustomerViewModelTest.kt`

- [ ] **Step 1: Test thất bại — submit gọi create, set `created` khi thành công; chặn tên rỗng**

```kotlin
package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.feature.customer.data.CustomerRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test

class AddCustomerViewModelTest {
    private val repo = mockk<CustomerRepository>(relaxed = true)
    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `submit with blank name sets error and does not call create`() = runTest {
        val vm = AddCustomerViewModel(repo)
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertEquals("Vui lòng nhập tên khách hàng", vm.state.value.errorMessage)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `submit success sets created`() = runTest {
        coEvery { repo.create(any()) } returns ApiResult.Success(CustomerDetailDto(id = 9, name = "Anh Năm"))
        val vm = AddCustomerViewModel(repo)
        vm.onName("Anh Năm")
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertNotNull(vm.state.value.created)
        coVerify { repo.create(CustomerCreateDto(name = "Anh Năm")) }
    }
}
```

- [ ] **Step 2: Chạy → FAIL**

Run: `./gradlew :app:testDebugUnitTest --tests "*AddCustomerViewModelTest*"`
Expected: FAIL — chưa có class.

- [ ] **Step 3: Viết ViewModel (bám AddSupplierViewModel)**

```kotlin
package com.mykiot.pos.feature.customer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.feature.customer.data.CustomerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AddCustomerUiState(
    val name: String = "",
    val phone: String = "",
    val email: String = "",
    val address: String = "",
    val note: String = "",
    val saving: Boolean = false,
    val created: CustomerDetailDto? = null,
    val errorMessage: String? = null,
)

@HiltViewModel
class AddCustomerViewModel @Inject constructor(
    private val repository: CustomerRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AddCustomerUiState())
    val state: StateFlow<AddCustomerUiState> = _state.asStateFlow()

    fun onName(v: String) = _state.update { it.copy(name = v) }
    fun onPhone(v: String) = _state.update { it.copy(phone = v) }
    fun onEmail(v: String) = _state.update { it.copy(email = v) }
    fun onAddress(v: String) = _state.update { it.copy(address = v) }
    fun onNote(v: String) = _state.update { it.copy(note = v) }
    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun submit() {
        val s = _state.value
        if (s.name.isBlank()) {
            _state.update { it.copy(errorMessage = "Vui lòng nhập tên khách hàng") }
            return
        }
        _state.update { it.copy(saving = true, errorMessage = null) }
        viewModelScope.launch {
            val body = CustomerCreateDto(
                name = s.name.trim(),
                phone = s.phone.trim().ifBlank { null },
                email = s.email.trim().ifBlank { null },
                address = s.address.trim().ifBlank { null },
                note = s.note.trim().ifBlank { null },
            )
            when (val r = repository.create(body)) {
                is ApiResult.Success -> _state.update { it.copy(saving = false, created = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(saving = false, errorMessage = r.error.message) }
            }
        }
    }
}
```

- [ ] **Step 4: Chạy → PASS**

Run: `./gradlew :app:testDebugUnitTest --tests "*AddCustomerViewModelTest*"`
Expected: PASS (2 test).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/AddCustomerViewModel.kt \
        android/app/src/test/java/com/mykiot/pos/feature/customer/AddCustomerViewModelTest.kt
git commit -m "feat(android): AddCustomerViewModel + test"
```

### Task 1.9: AddCustomerScreen

**Files:**
- Create: `android/app/src/main/java/com/mykiot/pos/feature/customer/AddCustomerScreen.kt`

- [ ] **Step 1: Viết form (bám AddSupplierScreen: FormTopBar + AppTextField + nút Lưu + LoadingDialog)**

Các field: Tên (bắt buộc), SĐT (KeyboardType.Phone), Email, Địa chỉ, Ghi chú. `LaunchedEffect(state.created)` → gọi `onCreated(id)`. `LaunchedEffect(state.errorMessage)` → snackbar. Tham chiếu cấu trúc y hệt `AddSupplierScreen.kt` đã đọc.

```kotlin
package com.mykiot.pos.feature.customer

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.LoadingDialog

@Composable
fun AddCustomerScreen(
    onCreated: (Long) -> Unit,
    onCancel: () -> Unit,
    viewModel: AddCustomerViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }
    LaunchedEffect(state.created) { state.created?.let { onCreated(it.id) } }
    if (state.saving) LoadingDialog()

    Scaffold(
        topBar = { AppHeader(title = "Thêm khách hàng", onBack = onCancel, modifier = Modifier.padding(horizontal = 16.dp)) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            AppTextField(state.name, viewModel::onName, label = "Tên khách hàng *")
            Spacer(Modifier.height(8.dp))
            AppTextField(state.phone, viewModel::onPhone, label = "Số điện thoại", keyboardType = KeyboardType.Phone)
            Spacer(Modifier.height(8.dp))
            AppTextField(state.email, viewModel::onEmail, label = "Email")
            Spacer(Modifier.height(8.dp))
            AppTextField(state.address, viewModel::onAddress, label = "Địa chỉ")
            Spacer(Modifier.height(8.dp))
            AppTextField(state.note, viewModel::onNote, label = "Ghi chú")
            Spacer(Modifier.height(16.dp))
            Button(onClick = viewModel::submit, enabled = !state.saving, modifier = Modifier.fillMaxWidth()) {
                Text("Lưu khách hàng")
            }
        }
    }
}
```

> Kiểm chữ ký `AppTextField` (có tham số `keyboardType` không?) trong `core/ui/Components.kt` trước khi viết; chỉnh cho khớp. `LoadingDialog()` đã tồn tại ở `core/ui/LoadingDialog.kt`.

- [ ] **Step 2: Build**

Run: `./gradlew :app:compileDebugKotlin`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/customer/AddCustomerScreen.kt
git commit -m "feat(android): AddCustomerScreen"
```

### Task 1.10: Nối Khách hàng vào HomeNavHost

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt`

- [ ] **Step 1: Thay placeholder bằng màn thật**

```kotlin
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
        ) { backStackEntry ->
            val id = backStackEntry.arguments?.getLong("id") ?: 0L
            CustomerDetailScreen(customerId = id, onBack = { nav.popBackStack() })
        }
        composable(Routes.CUSTOMER_ADD) {
            AddCustomerScreen(
                onCreated = { nav.popBackStack() },   // tạo xong quay lại DS
                onCancel = { nav.popBackStack() },
            )
        }
```

Thêm import:
```kotlin
import com.mykiot.pos.feature.customer.AddCustomerScreen
import com.mykiot.pos.feature.customer.CustomerDetailScreen
import com.mykiot.pos.feature.customer.CustomerListScreen
```

> Sau khi tạo xong KH muốn DS tự refresh: `CustomerListScreen` đã `LaunchedEffect(Unit){ load() }` — khi pop back về, nếu màn được tạo lại sẽ load lại. Nếu Compose giữ state cũ (không reload), cân nhắc dùng `savedStateHandle`/shared result; chấp nhận hành vi reload-on-enter cho MVP.

- [ ] **Step 2: Build + verify thủ công luồng đầy đủ**

Run: `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL. Trên app: Khác → Khách hàng → thấy DS, tìm theo tên hoạt động; bấm 1 KH → chi tiết + lịch sử; back; FAB (+) → form → Lưu → quay lại DS thấy KH mới.

- [ ] **Step 3: Chạy toàn bộ unit test**

Run: `./gradlew :app:testDebugUnitTest`
Expected: PASS toàn bộ (gồm 5 test mới của customer + các test cũ).

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt
git commit -m "feat(android): nối màn Khách hàng vào điều hướng Home"
```

---

## PHASES 2–5 — Spec để bung plan riêng

> Mỗi phase dưới đây là một vertical slice **giống hệt pattern Phase 1** (Api → DTO → Repository → ViewModel + test → Screen → nối nav). Khi tới lượt, dùng lại skill `writing-plans` để bung mỗi phase thành các task bite-sized như Phase 1. Liệt kê ở đây để chốt phạm vi + endpoint + điểm khác biệt.

### PHASE 2 — Sản phẩm (DS / chi tiết / sửa)

- **Endpoints:** `GET /products` (phân trang/lọc), `GET /products/{id}`, `PUT /products/{id}`. (Search `GET /products/search` đã có trong `ProductApi`.)
- **Mở rộng:** `ProductApi` thêm `list`, `get(id)`, `update`; `ProductDtos` thêm `ProductDetailDto`, `ProductUpdateDto` (đã có `ProductBriefDto`, `ProductCreateDto`).
- **Files mới:** `feature/product/ProductListScreen+VM+UiState`, `ProductDetailScreen+VM+UiState`. **Tái dùng** `AddProductScreen`/`AddProductViewModel` cho luồng tạo; thêm chế độ "sửa" (truyền `productId` + prefill).
- **Tách role (để hướng B):** ẩn `cost_price` (giá vốn) và nút "Ngừng bán" với CASHIER → **chưa làm ở đây**, chừa chỗ. Hiện tại detail có thể hiển thị giá vốn nếu backend trả (backend đã strip theo `show_cost_to_cashier`).
- **Nav:** `Routes.PRODUCTS` → list; `Routes.productDetail(id)` → detail; FAB → AddProduct (mode create). Thay placeholder trong `HomeNavHost`.
- **Tests:** `ProductListViewModelTest`, `ProductDetailViewModelTest` (mock repo, success/failure) — y như customer.

### PHASE 3 — Hóa đơn (lịch sử / chi tiết / in lại)

- **Endpoints:** `GET /invoices` (lịch sử, phân trang), `GET /invoices/{id}` (đã có trong `SalesApi`). (Hủy hóa đơn COMPLETED = OWNER → hướng B.)
- **Mở rộng:** `SalesApi` thêm `list(...)`; `SalesDtos` thêm `InvoiceListItemDto` + `InvoiceListDto` (code, total, status, completed_at, customer_name?).
- **Files mới:** `feature/invoicehistory/InvoiceHistoryScreen+VM+UiState`, `InvoiceDetailScreen+VM+UiState`.
- **In lại bill:** tái dùng `core/hardware/printer/EscPosReceiptPrinter` + `ReceiptLayout` (đã có) — nút "In lại" ở màn chi tiết, dựng `ReceiptLayout` từ `InvoiceDto`.
- **Nav:** `Routes.INVOICE_HISTORY` → list; `Routes.invoiceDetail(id)` → detail. Thay placeholder.
- **Tests:** `InvoiceHistoryViewModelTest`, `InvoiceDetailViewModelTest`.

### PHASE 4 — Trả hàng (returns)

- **Endpoints (xác minh ở backend `modules/sales` hoặc `returns`):** tạo phiếu trả từ hóa đơn + DS phiếu trả. Web đã có `pages/returns` (`ReturnList`, `ReturnForm`) → soi route web `/returns`, `/returns/new` để biết payload.
- **Tạo mới:** `core/network/ReturnApi.kt` + provider trong `NetworkModule` + `dto/ReturnDtos.kt`.
- **Files mới:** `feature/returns/ReturnListScreen+VM`, `ReturnFormScreen+VM` (chọn hóa đơn gốc → chọn SP + số lượng trả → hoàn tất).
- **Nav:** `Routes.RETURNS` → list; `Routes.RETURN_NEW` → form. Thay placeholder.
- **Tests:** `ReturnListViewModelTest`, `ReturnFormViewModelTest` (validate số lượng trả ≤ đã mua).
- **Lưu ý:** đây là phase phức tạp nhất (liên quan hóa đơn gốc + tồn kho hoàn lại) → bung plan riêng kỹ, đối chiếu backend trước.

### PHASE 5 — Đổi mật khẩu

- **Endpoint:** `PUT /auth/change-password` (body: old_password, new_password).
- **Mở rộng:** `AuthApi` thêm `changePassword`; `AuthDtos` thêm `ChangePasswordRequest`.
- **Files mới:** `feature/account/ChangePasswordScreen+VM`.
- **Validate (tiếng Việt — theo CLAUDE.md):** mật khẩu mới ≥ 6 ký tự ("Mật khẩu phải có ít nhất 6 ký tự"), xác nhận khớp ("Mật khẩu xác nhận không khớp").
- **Nav:** `Routes.CHANGE_PASSWORD`. Thay placeholder.
- **Tests:** `ChangePasswordViewModelTest` (chặn mật khẩu ngắn / không khớp; gọi API khi hợp lệ).

---

## Self-Review notes

- **Spec coverage:** Phase 0 (nav) + Phase 1 (Khách hàng) chi tiết đầy đủ; Phases 2–5 có spec endpoint/file/test rõ ràng, đánh dấu "bung plan riêng". Tất cả 5 khoảng trống hướng A trong báo cáo đối chiếu đều có phase tương ứng.
- **Ràng buộc tiếng Việt:** mọi message lỗi/validate trong plan đều tiếng Việt (theo CLAUDE.md + memory feedback_vietnamese_errors).
- **Tách role:** các nút OWNER-only (Xóa KH, Ngừng bán SP, Hủy hóa đơn COMPLETED) cố tình loại khỏi plan này, ghi chú rõ phụ thuộc hướng B. Phần tiền nhạy cảm (giá vốn/lợi nhuận) vẫn an toàn vì backend tự strip.
- **Điểm cần xác minh khi execute (không phải placeholder, là kiểm chứng codebase):** chữ ký `AppHeader`(có `onBack`?) và `AppTextField`(có `keyboardType`?) trong `core/ui/Components.kt`; sự tồn tại endpoint trả hàng ở backend trước Phase 4.
```
