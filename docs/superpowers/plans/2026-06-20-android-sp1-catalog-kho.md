# Android SP-1 — Catalog & Kho vận hành + Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung cho app Android các màn Nhà cung cấp, Nhóm hàng, Lịch sử phiếu nhập, Tồn kho + tab "Sắp hết", cùng nền tảng session/role-gating và component lỗi `ErrorDialog`.

**Architecture:** Giữ nguyên kiến trúc MVVM + Jetpack Compose + Hilt sẵn có: mỗi màn gồm `Screen` (Compose) + `UiState` + `@HiltViewModel` + `Repository` (gọi Retrofit `Api`) trả `ApiResult`, dùng `ErrorMapper`, điều hướng qua `HomeNavHost`/`Routes`, chuỗi qua `strings.xml`/`ResProvider`. Foundation thêm `SessionManager` (StateFlow role, persist trong `EncryptedTokenStore`) và `ErrorDialog` thay toast/snackbar cho mọi lỗi.

**Tech Stack:** Kotlin, Jetpack Compose, Material 3, Hilt, Retrofit + kotlinx.serialization, Coroutines/StateFlow. Test: JUnit4 + MockK + kotlinx-coroutines-test.

## Global Constraints

- Mọi text hiển thị cho người dùng (nhãn, empty-state, thông báo) phải **tiếng Việt**, khai báo trong `app/src/main/res/values/strings.xml` (Composable: `stringResource`; ViewModel: `ResProvider`). Không hardcode chuỗi tiếng Việt trong code.
- **Lỗi hiển thị bằng dialog `ErrorDialog`**, KHÔNG dùng Toast/Snackbar. Toast cho thông báo *thành công* được giữ.
- `error.code` giữ UPPER_SNAKE_CASE tiếng Anh; chỉ `message` tiếng Việt.
- Mọi query backend đã có sẵn — **KHÔNG sửa backend/web trong SP-1.**
- Mọi màn danh sách dùng base `PagingListViewModel<T>` + `PagedLazyColumn` khi response có `pagination`.
- Tiền dùng `core/util/Money.formatVnd(...)`; số lượng dùng `Money.formatQty(...)`; ngày dùng `Money.formatDateTime(...)`.
- Package gốc: `com.mykiot.pos`. Thư mục nguồn: `android/app/src/main/java/com/mykiot/pos/`. Test: `android/app/src/test/java/com/mykiot/pos/`.
- Lệnh build/test chạy từ thư mục `android/`: `./gradlew :app:testDebugUnitTest` và `./gradlew :app:assembleDebug`.

---

## File Structure

**Tạo mới:**
- `core/auth/SessionManager.kt` — nguồn sự thật in-memory về user/role (StateFlow).
- `core/ui/ErrorDialog.kt` — dialog lỗi dùng chung + `errorIconKind()` (hàm thuần, test được).
- `navigation/HubViewModel.kt` — cấp `CurrentUser?` cho Hub để gating.
- `feature/supplier/SupplierListScreen.kt`, `SupplierListViewModel.kt`, `SupplierListUiState.kt`.
- `feature/category/CategoryTreeScreen.kt`, `CategoryViewModel.kt`, `CategoryUiState.kt`, `data/CategoryRepository.kt`.
- `core/network/CategoryApi.kt`, `core/network/dto/CategoryDtos.kt`.
- `feature/receipt/GoodsReceiptListScreen.kt`, `GoodsReceiptListViewModel.kt`.
- Tests: `SessionManagerTest`, `ErrorIconKindTest`, `HubViewModelTest`, `SupplierListViewModelTest`, `AddSupplierViewModelTest`, `CategoryViewModelTest`, `GoodsReceiptListViewModelTest`, `InventoryViewModelTest` (mở rộng).

**Sửa:**
- `core/auth/TokenStore.kt`, `core/auth/EncryptedTokenStore.kt`, `src/test/.../core/auth/FakeTokenStore.kt` — persist `CurrentUser`.
- `core/auth/AuthRepository.kt` — set/clear session khi login/logout.
- `MainActivity.kt` — restore session khi cold start.
- `core/ui/paging/PagingState.kt`, `core/ui/paging/PagingListViewModel.kt` — `errorMessage: String?` → `error: ApiError?`.
- Các màn cũ dùng Snackbar/Toast → `ErrorDialog` (Task 5, 6).
- `navigation/HubScreen.kt` — gating + 3 thẻ mới.
- `navigation/Routes.kt`, `navigation/HomeNavHost.kt` — route mới.
- `core/network/SupplierApi.kt`, `core/network/dto/InventoryDtos.kt`, `feature/supplier/data/SupplierRepository.kt`, `feature/supplier/AddSupplierViewModel.kt`, `feature/supplier/AddSupplierScreen.kt`.
- `core/network/InventoryApi.kt`, `feature/receipt/data/ReceiptRepository.kt`.
- `core/network/NetworkModule.kt` — provide `CategoryApi`.
- `feature/inventory/InventoryViewModel.kt`, `InventoryUiState.kt`, `InventoryScreen.kt`.
- `res/values/strings.xml` — chuỗi mới.

---

# PHASE A — Foundation

### Task 1: TokenStore lưu CurrentUser

**Files:**
- Modify: `core/auth/TokenStore.kt`
- Modify: `core/auth/EncryptedTokenStore.kt`
- Modify (test): `src/test/java/com/mykiot/pos/core/auth/FakeTokenStore.kt`
- Test: `src/test/java/com/mykiot/pos/core/auth/FakeTokenStoreTest.kt` (mở rộng)

**Interfaces:**
- Consumes: `CurrentUser` (`core/auth/SessionState.kt`: `id: Long, fullName: String, role: String, tenantId: Long, tenantName: String`).
- Produces: `TokenStore.saveUser(user: CurrentUser)`, `TokenStore.getUser(): CurrentUser?`. `clear()` xóa cả user.

- [ ] **Step 1: Mở rộng test FakeTokenStore**

Thêm vào `FakeTokenStoreTest.kt`:

```kotlin
@Test
fun `saveUser then getUser returns same user`() {
    val store = FakeTokenStore()
    val user = CurrentUser(id = 7, fullName = "Chị Tư", role = "OWNER", tenantId = 3, tenantName = "Tạp hóa Tư")
    store.saveUser(user)
    assertEquals(user, store.getUser())
}

@Test
fun `clear removes saved user`() {
    val store = FakeTokenStore()
    store.saveUser(CurrentUser(1, "A", "CASHIER", 1, "Shop"))
    store.clear()
    assertNull(store.getUser())
}
```

Thêm import `org.junit.Assert.assertNull` và `com.mykiot.pos.core.auth.CurrentUser` nếu thiếu.

- [ ] **Step 2: Chạy test — kỳ vọng FAIL biên dịch (chưa có `saveUser`/`getUser`)**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.auth.FakeTokenStoreTest"`
Expected: FAIL — "unresolved reference: saveUser".

- [ ] **Step 3: Thêm method vào interface `TokenStore`**

```kotlin
package com.mykiot.pos.core.auth

interface TokenStore {
    fun getAccessToken(): String?
    fun getRefreshToken(): String?
    fun save(accessToken: String, refreshToken: String)
    fun saveUser(user: CurrentUser)
    fun getUser(): CurrentUser?
    fun clear()
    fun hasSession(): Boolean
}
```

- [ ] **Step 4: Cài đặt trong `EncryptedTokenStore`**

Thêm các key vào `companion object`:

```kotlin
const val KEY_USER_ID = "user_id"
const val KEY_USER_NAME = "user_name"
const val KEY_USER_ROLE = "user_role"
const val KEY_TENANT_ID = "tenant_id"
const val KEY_TENANT_NAME = "tenant_name"
```

Thêm method (đặt trước `clear()`):

```kotlin
override fun saveUser(user: CurrentUser) {
    prefs.edit()
        .putLong(KEY_USER_ID, user.id)
        .putString(KEY_USER_NAME, user.fullName)
        .putString(KEY_USER_ROLE, user.role)
        .putLong(KEY_TENANT_ID, user.tenantId)
        .putString(KEY_TENANT_NAME, user.tenantName)
        .apply()
}

override fun getUser(): CurrentUser? {
    val role = prefs.getString(KEY_USER_ROLE, null) ?: return null
    return CurrentUser(
        id = prefs.getLong(KEY_USER_ID, 0L),
        fullName = prefs.getString(KEY_USER_NAME, "") ?: "",
        role = role,
        tenantId = prefs.getLong(KEY_TENANT_ID, 0L),
        tenantName = prefs.getString(KEY_TENANT_NAME, "") ?: "",
    )
}
```

(`clear()` hiện đã gọi `prefs.edit().clear()` nên xóa luôn user — không cần sửa.)

- [ ] **Step 5: Cài đặt trong `FakeTokenStore`**

```kotlin
class FakeTokenStore : TokenStore {
    private var access: String? = null
    private var refresh: String? = null
    private var user: CurrentUser? = null

    override fun getAccessToken(): String? = access
    override fun getRefreshToken(): String? = refresh
    override fun save(accessToken: String, refreshToken: String) {
        access = accessToken; refresh = refresh.let { refreshToken }
    }
    override fun saveUser(user: CurrentUser) { this.user = user }
    override fun getUser(): CurrentUser? = user
    override fun clear() { access = null; refresh = null; user = null }
    override fun hasSession(): Boolean = access != null && refresh != null
}
```

- [ ] **Step 6: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.auth.FakeTokenStoreTest"`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/auth/TokenStore.kt \
        android/app/src/main/java/com/mykiot/pos/core/auth/EncryptedTokenStore.kt \
        android/app/src/test/java/com/mykiot/pos/core/auth/FakeTokenStore.kt \
        android/app/src/test/java/com/mykiot/pos/core/auth/FakeTokenStoreTest.kt
git commit -m "feat(auth): TokenStore persist CurrentUser cho cold-start role-gating"
```

---

### Task 2: SessionManager

**Files:**
- Create: `core/auth/SessionManager.kt`
- Test: `src/test/java/com/mykiot/pos/core/auth/SessionManagerTest.kt`

**Interfaces:**
- Consumes: `TokenStore.getUser()` (Task 1), `CurrentUser`.
- Produces: `SessionManager` (`@Singleton`): `val current: StateFlow<CurrentUser?>`, `fun set(user: CurrentUser)`, `fun clear()`, `fun restore()`, `val isOwner: Boolean`.

- [ ] **Step 1: Viết test thất bại**

`SessionManagerTest.kt`:

```kotlin
package com.mykiot.pos.core.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionManagerTest {
    private val owner = CurrentUser(1, "Chủ", "OWNER", 1, "Shop")
    private val cashier = CurrentUser(2, "Thu ngân", "CASHIER", 1, "Shop")

    @Test
    fun `set updates current and isOwner`() {
        val sm = SessionManager(FakeTokenStore())
        sm.set(owner)
        assertEquals(owner, sm.current.value)
        assertTrue(sm.isOwner)
    }

    @Test
    fun `restore reads persisted user from store`() {
        val store = FakeTokenStore().apply { saveUser(cashier) }
        val sm = SessionManager(store)
        sm.restore()
        assertEquals(cashier, sm.current.value)
        assertFalse(sm.isOwner)
    }

    @Test
    fun `clear empties current`() {
        val sm = SessionManager(FakeTokenStore())
        sm.set(owner)
        sm.clear()
        assertNull(sm.current.value)
        assertFalse(sm.isOwner)
    }
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL (chưa có SessionManager)**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.auth.SessionManagerTest"`
Expected: FAIL — "unresolved reference: SessionManager".

- [ ] **Step 3: Tạo `SessionManager.kt`**

```kotlin
package com.mykiot.pos.core.auth

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Nguồn sự thật in-memory về user/role của phiên hiện tại.
 * Persist nằm ở [TokenStore]; [restore] nạp lại khi cold-start.
 */
@Singleton
class SessionManager @Inject constructor(
    private val tokenStore: TokenStore,
) {
    private val _current = MutableStateFlow<CurrentUser?>(null)
    val current: StateFlow<CurrentUser?> = _current.asStateFlow()

    val isOwner: Boolean get() = _current.value?.role == "OWNER"

    fun set(user: CurrentUser) { _current.value = user }
    fun clear() { _current.value = null }
    fun restore() { _current.value = tokenStore.getUser() }
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.auth.SessionManagerTest"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/auth/SessionManager.kt \
        android/app/src/test/java/com/mykiot/pos/core/auth/SessionManagerTest.kt
git commit -m "feat(auth): SessionManager giữ StateFlow user/role toàn app"
```

---

### Task 3: Nối SessionManager vào AuthRepository + cold-start restore

**Files:**
- Modify: `core/auth/AuthRepository.kt`
- Modify: `MainActivity.kt`

**Interfaces:**
- Consumes: `SessionManager` (Task 2), `TokenStore.saveUser` (Task 1).
- Produces: sau `login()` thành công → user được persist + `SessionManager.current` cập nhật; `logout()` → clear; cold-start → `restore()`.

- [ ] **Step 1: Inject SessionManager vào AuthRepository**

Sửa constructor:

```kotlin
@Singleton
class AuthRepository @Inject constructor(
    private val api: AuthApi,
    private val tokenStore: TokenStore,
    private val errorMapper: ErrorMapper,
    private val sessionManager: SessionManager,
) {
```

- [ ] **Step 2: Persist + set session sau login thành công**

Trong nhánh `LoggedIn`, ngay sau `tokenStore.save(dto.accessToken, dto.refreshToken)`, thêm:

```kotlin
val currentUser = CurrentUser(
    id = dto.user.id,
    fullName = dto.user.fullName,
    role = dto.user.role,
    tenantId = dto.tenant.id,
    tenantName = dto.tenant.name,
)
tokenStore.saveUser(currentUser)
sessionManager.set(currentUser)
```

Và trả `LoginOutcome.LoggedIn(currentUser)` (thay vì dựng `CurrentUser(...)` inline lần nữa).

- [ ] **Step 3: Clear session khi logout**

Trong `logout()`, sau `tokenStore.clear()` thêm:

```kotlin
sessionManager.clear()
```

- [ ] **Step 4: Restore khi cold-start trong MainActivity**

Sửa `MainActivity`:

```kotlin
@Inject lateinit var tokenStore: TokenStore
@Inject lateinit var sessionManager: SessionManager

override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val loggedIn = tokenStore.hasSession()
    if (loggedIn) sessionManager.restore()
    setContent {
        ...
    }
}
```

Thêm import `com.mykiot.pos.core.auth.SessionManager`.

- [ ] **Step 5: Build — kỳ vọng biên dịch OK & test cũ xanh**

Run: `cd android && ./gradlew :app:testDebugUnitTest`
Expected: BUILD SUCCESSFUL (LoginViewModelTest mock AuthRepository nên không ảnh hưởng).

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/auth/AuthRepository.kt \
        android/app/src/main/java/com/mykiot/pos/MainActivity.kt
git commit -m "feat(auth): set/restore SessionManager khi login/logout/cold-start"
```

---

### Task 4: ErrorDialog component

**Files:**
- Create: `core/ui/ErrorDialog.kt`
- Test: `src/test/java/com/mykiot/pos/core/ui/ErrorIconKindTest.kt`

**Interfaces:**
- Consumes: `ApiError` (`code: String, message: String, httpStatus: Int?`).
- Produces: `enum class ErrorIconKind { NETWORK, PERMISSION, NOT_FOUND, GENERIC }`, `fun errorIconKind(error: ApiError): ErrorIconKind`, `@Composable fun ErrorDialog(error: ApiError, onDismiss: () -> Unit)`.

- [ ] **Step 1: Viết test thuần cho mapping icon**

`ErrorIconKindTest.kt`:

```kotlin
package com.mykiot.pos.core.ui

import com.mykiot.pos.core.network.ApiError
import org.junit.Assert.assertEquals
import org.junit.Test

class ErrorIconKindTest {
    @Test fun `network error maps to NETWORK`() =
        assertEquals(ErrorIconKind.NETWORK, errorIconKind(ApiError("NETWORK_ERROR", "Mất mạng", null)))

    @Test fun `401 maps to PERMISSION`() =
        assertEquals(ErrorIconKind.PERMISSION, errorIconKind(ApiError("X", "m", 401)))

    @Test fun `403 maps to PERMISSION`() =
        assertEquals(ErrorIconKind.PERMISSION, errorIconKind(ApiError("FORBIDDEN", "m", 403)))

    @Test fun `404 maps to NOT_FOUND`() =
        assertEquals(ErrorIconKind.NOT_FOUND, errorIconKind(ApiError("X", "m", 404)))

    @Test fun `400 maps to GENERIC`() =
        assertEquals(ErrorIconKind.GENERIC, errorIconKind(ApiError("VALIDATION", "m", 400)))

    @Test fun `500 maps to GENERIC`() =
        assertEquals(ErrorIconKind.GENERIC, errorIconKind(ApiError("X", "m", 500)))
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.ui.ErrorIconKindTest"`
Expected: FAIL — "unresolved reference: errorIconKind".

- [ ] **Step 3: Tạo `ErrorDialog.kt`**

```kotlin
package com.mykiot.pos.core.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.SearchOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import com.mykiot.pos.R
import com.mykiot.pos.core.network.ApiError

enum class ErrorIconKind { NETWORK, PERMISSION, NOT_FOUND, GENERIC }

/** Suy loại icon từ ApiError — hàm thuần để unit-test không cần Compose. */
fun errorIconKind(error: ApiError): ErrorIconKind = when {
    error.httpStatus == null && error.code == "NETWORK_ERROR" -> ErrorIconKind.NETWORK
    error.httpStatus == 401 || error.httpStatus == 403 -> ErrorIconKind.PERMISSION
    error.httpStatus == 404 -> ErrorIconKind.NOT_FOUND
    else -> ErrorIconKind.GENERIC
}

private fun ErrorIconKind.icon(): ImageVector = when (this) {
    ErrorIconKind.NETWORK -> Icons.Outlined.CloudOff
    ErrorIconKind.PERMISSION -> Icons.Outlined.Lock
    ErrorIconKind.NOT_FOUND -> Icons.Outlined.SearchOff
    ErrorIconKind.GENERIC -> Icons.Outlined.ErrorOutline
}

/**
 * Dialog hiển thị lỗi dùng chung toàn app (thay Toast/Snackbar).
 * Gồm icon theo loại lỗi, mô tả tiếng Việt, một nút "Đóng".
 */
@Composable
fun ErrorDialog(error: ApiError, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {
            Icon(
                errorIconKind(error).icon(),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.error,
            )
        },
        title = { Text(stringResource(R.string.common_error_title)) },
        text = { Text(error.message) },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.common_close)) }
        },
    )
}
```

- [ ] **Step 4: Thêm chuỗi vào `res/values/strings.xml`**

```xml
<string name="common_error_title">Đã xảy ra lỗi</string>
<string name="common_close">Đóng</string>
```

- [ ] **Step 5: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.core.ui.ErrorIconKindTest"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/ErrorDialog.kt \
        android/app/src/test/java/com/mykiot/pos/core/ui/ErrorIconKindTest.kt \
        android/app/src/main/res/values/strings.xml
git commit -m "feat(ui): ErrorDialog dùng chung + errorIconKind (test)"
```

---

### Task 5: Migrate lỗi danh sách phân trang sang ErrorDialog

**Files:**
- Modify: `core/ui/paging/PagingState.kt`, `core/ui/paging/PagingListViewModel.kt`
- Modify (screens dùng paging): `feature/customer/CustomerListScreen.kt`, `feature/product/ProductListScreen.kt`, `feature/inventory/InventoryScreen.kt`, `feature/invoice/InvoiceListScreen.kt`, `feature/invoice/ReturnsScreen.kt`
- Modify (tests): `feature/customer/CustomerListViewModelTest.kt`, `feature/product/ProductListViewModelTest.kt`, `feature/invoice/InvoiceListViewModelTest.kt`, `feature/invoice/ReturnsViewModelTest.kt`, `feature/inventory/InventoryViewModelTest.kt` — đổi `errorMessage` → `error?.message`.

**Interfaces:**
- Produces: `PagingState.error: ApiError?` (thay `errorMessage: String?`); `PagingListViewModel.setError(error: ApiError?)`; `clearError()` giữ nguyên tên.

- [ ] **Step 1: Đổi field trong `PagingState`**

```kotlin
import com.mykiot.pos.core.network.ApiError

data class PagingState<T>(
    val items: List<T> = emptyList(),
    val page: Int = 0,
    val totalPages: Int = 1,
    val refreshing: Boolean = false,
    val loadingMore: Boolean = false,
    val error: ApiError? = null,
) {
    val canLoadMore: Boolean
        get() = page in 1 until totalPages && !loadingMore && !refreshing
    val isEmpty: Boolean get() = items.isEmpty()
}
```

- [ ] **Step 2: Cập nhật `PagingListViewModel`**

Thay mọi `errorMessage = null` → `error = null`; trong nhánh `is ApiResult.Failure` của `refresh()` và `loadMore()` đổi `errorMessage = r.error.message` → `error = r.error`. Sửa:

```kotlin
protected fun setError(error: ApiError?) = _paging.update { it.copy(error = error) }
fun clearError() = _paging.update { it.copy(error = null) }
```

Thêm import `com.mykiot.pos.core.network.ApiError`.

- [ ] **Step 3: Cập nhật từng màn paging — thay Snackbar bằng ErrorDialog**

Recipe áp dụng cho **từng** file màn liệt kê ở trên. Xóa khối `SnackbarHost` + `LaunchedEffect(... errorMessage ...)` liên quan tới lỗi paging, thêm:

```kotlin
val paging by viewModel.paging.collectAsStateWithLifecycle()
// ... cuối Composable, trong cùng scope hiển thị:
paging.error?.let { com.mykiot.pos.core.ui.ErrorDialog(it) { viewModel.clearError() } }
```

Nếu màn vẫn còn Snackbar cho mục đích khác (thành công), giữ lại Snackbar nhưng bỏ phần đọc lỗi paging. Áp dụng cho: `CustomerListScreen`, `ProductListScreen`, `InvoiceListScreen`, `ReturnsScreen`. (`InventoryScreen` sẽ chỉnh đầy đủ ở Task 22 — ở đây chỉ cần đổi đọc `paging.error` cho biên dịch.)

- [ ] **Step 4: Cập nhật test đọc errorMessage**

Trong các test paging, đổi mọi `vm.paging.value.errorMessage` → `vm.paging.value.error?.message`. Ví dụ trong `CustomerListViewModelTest`:

```kotlin
assertEquals("Lỗi tải", vm.paging.value.error?.message)
```

- [ ] **Step 5: Build + test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest`
Expected: BUILD SUCCESSFUL, tất cả test xanh.

- [ ] **Step 6: assembleDebug để chắc chắn Compose biên dịch**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/ui/paging android/app/src/main/java/com/mykiot/pos/feature android/app/src/test/java/com/mykiot/pos/feature
git commit -m "refactor(ui): paging lỗi dùng ErrorDialog thay Snackbar"
```

---

### Task 6: Migrate màn không-paging sang ErrorDialog

**Files:**
- Modify: `feature/account/ChangePasswordScreen.kt` + `ChangePasswordViewModel.kt`, `feature/customer/AddCustomerScreen.kt` + `AddCustomerViewModel.kt`, `feature/product/AddProductScreen.kt` + `AddProductViewModel.kt`, `feature/invoice/ReturnFormScreen.kt` + `ReturnFormViewModel.kt`, `feature/pos/PosScreen.kt` + `PosViewModel.kt`, `feature/receipt/GoodsReceiptDetailScreen.kt` (+ VM tương ứng)
- Modify (tests): các `*ViewModelTest` đọc `errorMessage` → `error?.message`.

**Interfaces:**
- Produces: mỗi `UiState` không-paging dùng `error: ApiError?` thay `errorMessage: String?`; VM set `r.error`; `clearError()` set null.

- [ ] **Step 1: Recipe ViewModel**

Cho mỗi VM ở trên: trong `data class ...UiState`, đổi `val errorMessage: String? = null` → `val error: ApiError? = null` (thêm `import com.mykiot.pos.core.network.ApiError`). Mọi chỗ `errorMessage = r.error.message` → `error = r.error`. Mọi chỗ set lỗi validation từ `ResProvider` (chuỗi thuần) → bọc thành `ApiError("VALIDATION", res.get(...))`. `clearError()` → `it.copy(error = null)`.

Ví dụ `AddSupplierViewModel`-style validation:

```kotlin
_state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_supplier_err_name_required))) }
```

- [ ] **Step 2: Recipe Screen**

Cho mỗi Screen: xóa `SnackbarHost`/`LaunchedEffect(state.errorMessage){...showSnackbar...}`. Thêm cuối Composable:

```kotlin
state.error?.let { com.mykiot.pos.core.ui.ErrorDialog(it) { viewModel.clearError() } }
```

- [ ] **Step 3: Cập nhật test**

Đổi mọi assert `...errorMessage` → `...error?.message`. Với test so khớp chuỗi `ResProvider` (vd ChangePassword), đổi:

```kotlin
assertEquals(res.get(R.string.misc_change_password_min_length), vm.state.value.error?.message)
```

- [ ] **Step 4: Build + test**

Run: `cd android && ./gradlew :app:testDebugUnitTest`
Expected: BUILD SUCCESSFUL, test xanh.

- [ ] **Step 5: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature android/app/src/test/java/com/mykiot/pos/feature
git commit -m "refactor(ui): màn form/POS dùng ErrorDialog thay Snackbar/Toast"
```

---

### Task 7: HubViewModel + role-gating

**Files:**
- Create: `navigation/HubViewModel.kt`
- Modify: `navigation/HubScreen.kt`
- Test: `src/test/java/com/mykiot/pos/navigation/HubViewModelTest.kt`

**Interfaces:**
- Consumes: `SessionManager.current` (Task 2).
- Produces: `HubViewModel` (`@HiltViewModel`): `val user: StateFlow<CurrentUser?>`. `HubScreen` lọc bỏ `HubItem.ownerOnly` khi `user.role != "OWNER"`.

- [ ] **Step 1: Viết test HubViewModel**

```kotlin
package com.mykiot.pos.navigation

import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.auth.FakeTokenStore
import org.junit.Assert.assertEquals
import org.junit.Test

class HubViewModelTest {
    @Test
    fun `exposes current user from session`() {
        val sm = SessionManager(FakeTokenStore())
        sm.set(CurrentUser(1, "Chủ", "OWNER", 1, "Shop"))
        val vm = HubViewModel(sm)
        assertEquals("OWNER", vm.user.value?.role)
    }
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.navigation.HubViewModelTest"`
Expected: FAIL — "unresolved reference: HubViewModel".

- [ ] **Step 3: Tạo `HubViewModel.kt`**

```kotlin
package com.mykiot.pos.navigation

import androidx.lifecycle.ViewModel
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class HubViewModel @Inject constructor(
    sessionManager: SessionManager,
) : ViewModel() {
    val user: StateFlow<CurrentUser?> = sessionManager.current
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.navigation.HubViewModelTest"`
Expected: PASS.

- [ ] **Step 5: Gating trong `HubScreen`**

Trong `HubScreen`, thêm tham số `viewModel: HubViewModel = hiltViewModel()` và lọc nhóm:

```kotlin
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable
fun HubScreen(
    onNavigate: (String) -> Unit,
    onOpenPos: () -> Unit,
    onLogout: () -> Unit,
    viewModel: HubViewModel = hiltViewModel(),
) {
    val user by viewModel.user.collectAsStateWithLifecycle()
    val isOwner = user?.role == "OWNER"
    val visibleGroups = hubGroups
        .map { g -> g.copy(items = g.items.filter { !it.ownerOnly || isOwner }) }
        .filter { it.items.isNotEmpty() }
    // ... thay `hubGroups.forEachIndexed` bằng `visibleGroups.forEachIndexed`
```

(`HubGroup` là `data class` nên `copy(items = ...)` dùng được.)

- [ ] **Step 6: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation/HubViewModel.kt \
        android/app/src/main/java/com/mykiot/pos/navigation/HubScreen.kt \
        android/app/src/test/java/com/mykiot/pos/navigation/HubViewModelTest.kt
git commit -m "feat(hub): role-gating ẩn thẻ ownerOnly với CASHIER"
```

---

# PHASE B — Nhà cung cấp

### Task 8: Mở rộng Supplier DTO/Api/Repository

**Files:**
- Modify: `core/network/dto/InventoryDtos.kt`
- Modify: `core/network/SupplierApi.kt`
- Modify: `feature/supplier/data/SupplierRepository.kt`

**Interfaces:**
- Produces:
  - `SupplierListDto(items, pagination: PaginationDto?)`
  - `SupplierResponseDto(id, name, phone?, email?, address?, taxCode?, note?, totalDebt)`
  - `SupplierApi.list(search, page, limit): SupplierListDto`, `getById(id): SupplierResponseDto`, `update(id, body: SupplierCreateDto): SupplierResponseDto`
  - `SupplierRepository.list(search, page): ApiResult<PageResult<SupplierDto>>`, `getById(id): ApiResult<SupplierResponseDto>`, `update(id, body): ApiResult<SupplierResponseDto>`, `create` (giữ).

- [ ] **Step 1: Cập nhật DTO trong `InventoryDtos.kt`**

Đổi `SupplierListDto` và thêm `SupplierResponseDto`:

```kotlin
@Serializable
data class SupplierListDto(
    val items: List<SupplierDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

@Serializable
data class SupplierResponseDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    @SerialName("tax_code") val taxCode: String? = null,
    val note: String? = null,
    @SerialName("total_debt") val totalDebt: Double = 0.0,
)
```

- [ ] **Step 2: Cập nhật `SupplierApi`**

```kotlin
interface SupplierApi {
    @GET("suppliers") suspend fun list(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): SupplierListDto

    @GET("suppliers/{id}") suspend fun getById(@Path("id") id: Long): SupplierResponseDto

    @POST("suppliers") suspend fun create(@Body body: SupplierCreateDto): SupplierDto

    @PUT("suppliers/{id}") suspend fun update(
        @Path("id") id: Long,
        @Body body: SupplierCreateDto,
    ): SupplierResponseDto
}
```

Thêm import `retrofit2.http.Path`, `retrofit2.http.PUT`, và DTO mới.

- [ ] **Step 3: Cập nhật `SupplierRepository`**

```kotlin
open class SupplierRepository @Inject constructor(
    private val supplierApi: SupplierApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?, page: Int = 1): ApiResult<PageResult<SupplierDto>> =
        runCatching {
            val r = supplierApi.list(search = search, page = page)
            PageResult.from(r.items, r.pagination)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun getById(id: Long): ApiResult<SupplierResponseDto> =
        runCatching { supplierApi.getById(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(dto: SupplierCreateDto): ApiResult<SupplierDto> =
        runCatching { supplierApi.create(dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun update(id: Long, dto: SupplierCreateDto): ApiResult<SupplierResponseDto> =
        runCatching { supplierApi.update(id, dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

Thêm import `PageResult`, `SupplierDto`, `SupplierResponseDto`.

- [ ] **Step 4: Build (đảm bảo `ReceiptRepository.list` vẫn biên dịch — `.items` còn nguyên)**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/dto/InventoryDtos.kt \
        android/app/src/main/java/com/mykiot/pos/core/network/SupplierApi.kt \
        android/app/src/main/java/com/mykiot/pos/feature/supplier/data/SupplierRepository.kt
git commit -m "feat(supplier): API list phân trang + getById + update"
```

---

### Task 9: SupplierListViewModel

**Files:**
- Create: `feature/supplier/SupplierListViewModel.kt`
- Test: `src/test/java/com/mykiot/pos/feature/supplier/SupplierListViewModelTest.kt`

**Interfaces:**
- Consumes: `SupplierRepository.list` (Task 8).
- Produces: `SupplierListViewModel : PagingListViewModel<SupplierDto>` với `load()`, `onQueryChange(q)`, `val query: StateFlow<String>`.

- [ ] **Step 1: Viết test**

```kotlin
package com.mykiot.pos.feature.supplier

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.feature.supplier.data.SupplierRepository
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

class SupplierListViewModelTest {
    private val repo = mockk<SupplierRepository>()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load populates suppliers`() = runTest {
        coEvery { repo.list(null, any()) } returns ApiResult.Success(
            PageResult(listOf(SupplierDto(1, "NCC A", "0900000000", 50000.0)), 1, 1),
        )
        val vm = SupplierListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(1, vm.paging.value.items.size)
        assertEquals("NCC A", vm.paging.value.items.first().name)
    }

    @Test
    fun `load sets error on failure`() = runTest {
        coEvery { repo.list(null, any()) } returns ApiResult.Failure(ApiError("X", "Lỗi tải NCC"))
        val vm = SupplierListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals("Lỗi tải NCC", vm.paging.value.error?.message)
    }
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.supplier.SupplierListViewModelTest"`
Expected: FAIL — "unresolved reference: SupplierListViewModel".

- [ ] **Step 3: Tạo VM**

```kotlin
package com.mykiot.pos.feature.supplier

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
import com.mykiot.pos.feature.supplier.data.SupplierRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject

@HiltViewModel
class SupplierListViewModel @Inject constructor(
    private val repository: SupplierRepository,
) : PagingListViewModel<SupplierDto>() {

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    fun load() = refresh()

    override suspend fun fetch(page: Int): ApiResult<PageResult<SupplierDto>> =
        repository.list(_query.value.takeIf { it.isNotBlank() }, page)

    fun onQueryChange(q: String) {
        _query.value = q
        if (q.isBlank() || q.length >= 2) refresh()
    }
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.supplier.SupplierListViewModelTest"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/supplier/SupplierListViewModel.kt \
        android/app/src/test/java/com/mykiot/pos/feature/supplier/SupplierListViewModelTest.kt
git commit -m "feat(supplier): SupplierListViewModel (paging + search)"
```

---

### Task 10: SupplierListScreen

**Files:**
- Create: `feature/supplier/SupplierListScreen.kt`
- Modify: `res/values/strings.xml`

**Interfaces:**
- Consumes: `SupplierListViewModel` (Task 9), `PagedLazyColumn`, `ErrorDialog`, `Money.formatVnd`.
- Produces: `@Composable fun SupplierListScreen(onBack, onAdd, onEdit: (Long) -> Unit, viewModel = hiltViewModel())`.

- [ ] **Step 1: Thêm chuỗi vào `strings.xml`**

```xml
<string name="cat_supplier_list_title">Nhà cung cấp</string>
<string name="cat_supplier_search_hint">Tìm theo tên / SĐT</string>
<string name="cat_supplier_empty">Chưa có nhà cung cấp</string>
<string name="cat_supplier_debt_label">Công nợ</string>
<string name="cat_supplier_add_action">Thêm nhà cung cấp</string>
```

- [ ] **Step 2: Tạo `SupplierListScreen.kt`**

```kotlin
package com.mykiot.pos.feature.supplier

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import com.mykiot.pos.core.util.formatVnd

@Composable
fun SupplierListScreen(
    onBack: () -> Unit,
    onAdd: () -> Unit,
    onEdit: (Long) -> Unit,
    viewModel: SupplierListViewModel = hiltViewModel(),
) {
    val paging by viewModel.paging.collectAsStateWithLifecycle()
    val query by viewModel.query.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = { AppHeader(title = stringResource(R.string.cat_supplier_list_title), onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onAdd,
                icon = { Icon(Icons.Outlined.Add, contentDescription = null) },
                text = { Text(stringResource(R.string.cat_supplier_add_action)) },
            )
        },
    ) { padding ->
        Column(Modifier.padding(padding).padding(horizontal = 16.dp)) {
            AppTextField(
                value = query,
                onValueChange = viewModel::onQueryChange,
                label = stringResource(R.string.cat_supplier_search_hint),
                modifier = Modifier.fillMaxWidth(),
            )
            PagedLazyColumn(
                state = paging,
                onLoadMore = viewModel::loadMore,
                emptyText = stringResource(R.string.cat_supplier_empty),
                key = { it.id },
            ) { supplier -> SupplierRow(supplier, onClick = { onEdit(supplier.id) }) }
        }
    }

    paging.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun SupplierRow(supplier: SupplierDto, onClick: () -> Unit) {
    Surface(onClick = onClick, color = MaterialTheme.colorScheme.surface, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.fillMaxWidth().padding(14.dp)) {
            Text(supplier.name, style = MaterialTheme.typography.titleMedium)
            supplier.phone?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            Text(
                stringResource(R.string.cat_supplier_debt_label) + ": " + formatVnd(supplier.totalDebt.toLong()),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
            )
        }
    }
}
```

> **Lưu ý khi thực thi:** kiểm tra chữ ký thực tế của `PagedLazyColumn` trong `core/ui/paging/PagedLazyColumn.kt` và khớp đúng tham số (`state`/`onLoadMore`/`emptyText`/`key`/itemContent). Nếu khác, điều chỉnh lời gọi cho khớp — giữ nguyên ý: list phân trang + empty-state.

- [ ] **Step 3: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/supplier/SupplierListScreen.kt \
        android/app/src/main/res/values/strings.xml
git commit -m "feat(supplier): SupplierListScreen (tìm kiếm + công nợ + FAB thêm)"
```

---

### Task 11: AddSupplier — chế độ Sửa

**Files:**
- Modify: `feature/supplier/AddSupplierViewModel.kt`
- Modify: `feature/supplier/AddSupplierScreen.kt`
- Test: `src/test/java/com/mykiot/pos/feature/supplier/AddSupplierViewModelTest.kt`

**Interfaces:**
- Consumes: `SupplierRepository.getById/update/create` (Task 8).
- Produces: `AddSupplierViewModel.startEdit(id: Long)` nạp dữ liệu; `submit()` gọi `update` nếu đang sửa, `create` nếu thêm. `AddSupplierUiState.editingId: Long?`.

- [ ] **Step 1: Viết test create vs edit**

```kotlin
package com.mykiot.pos.feature.supplier

import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.SupplierCreateDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.network.dto.SupplierResponseDto
import com.mykiot.pos.feature.supplier.data.SupplierRepository
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
import org.junit.Before
import org.junit.Test

class AddSupplierViewModelTest {
    private val repo = mockk<SupplierRepository>(relaxed = true)
    private val res = FakeResProvider()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `blank name sets error, no api call`() = runTest {
        val vm = AddSupplierViewModel(repo, res)
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(com.mykiot.pos.R.string.cat_supplier_err_name_required), vm.state.value.error?.message)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `create path calls repo create`() = runTest {
        coEvery { repo.create(any()) } returns ApiResult.Success(SupplierDto(1, "NCC A", null, 0.0))
        val vm = AddSupplierViewModel(repo, res)
        vm.onName("NCC A")
        vm.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.create(SupplierCreateDto(name = "NCC A", phone = null, address = null)) }
    }

    @Test
    fun `startEdit loads then submit calls update`() = runTest {
        coEvery { repo.getById(9) } returns ApiResult.Success(
            SupplierResponseDto(9, "NCC Cũ", "0901", null, "Đ/c", null, null, 0.0),
        )
        coEvery { repo.update(eq(9), any()) } returns ApiResult.Success(
            SupplierResponseDto(9, "NCC Mới", "0901", null, "Đ/c", null, null, 0.0),
        )
        val vm = AddSupplierViewModel(repo, res)
        vm.startEdit(9)
        testScheduler.advanceUntilIdle()
        assertEquals("NCC Cũ", vm.state.value.name)
        vm.onName("NCC Mới")
        vm.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.update(eq(9), any()) }
    }
}
```

(`eq` từ `io.mockk.eq`.)

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.supplier.AddSupplierViewModelTest"`
Expected: FAIL — "unresolved reference: startEdit" / `error`.

- [ ] **Step 3: Cập nhật `AddSupplierViewModel`**

```kotlin
data class AddSupplierUiState(
    val name: String = "",
    val phone: String = "",
    val address: String = "",
    val loading: Boolean = false,
    val error: ApiError? = null,
    val created: SupplierDto? = null,
    val saved: Boolean = false,
    val editingId: Long? = null,
)

@HiltViewModel
class AddSupplierViewModel @Inject constructor(
    private val repository: SupplierRepository,
    private val res: ResProvider,
) : ViewModel() {

    private val _state = MutableStateFlow(AddSupplierUiState())
    val state: StateFlow<AddSupplierUiState> = _state.asStateFlow()

    private var prefilled = false

    fun prefillName(name: String) {
        if (prefilled) return
        prefilled = true
        if (name.isNotBlank()) _state.update { it.copy(name = name) }
    }

    fun startEdit(id: Long) {
        if (_state.value.editingId == id) return
        _state.update { it.copy(editingId = id, loading = true) }
        viewModelScope.launch {
            when (val r = repository.getById(id)) {
                is ApiResult.Success -> _state.update {
                    it.copy(loading = false, name = r.data.name, phone = r.data.phone ?: "", address = r.data.address ?: "")
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun onName(v: String) = _state.update { it.copy(name = v) }
    fun onPhone(v: String) = _state.update { it.copy(phone = v) }
    fun onAddress(v: String) = _state.update { it.copy(address = v) }
    fun clearError() = _state.update { it.copy(error = null) }

    fun submit() {
        val s = _state.value
        if (s.name.isBlank()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_supplier_err_name_required))) }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            val dto = SupplierCreateDto(
                name = s.name.trim(),
                phone = s.phone.trim().ifBlank { null },
                address = s.address.trim().ifBlank { null },
            )
            val editId = s.editingId
            val result = if (editId != null) repository.update(editId, dto) else repository.create(dto)
            when (result) {
                is ApiResult.Success -> _state.update {
                    it.copy(loading = false, saved = true, created = (result.data as? SupplierDto))
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = result.error) }
            }
        }
    }
}
```

Thêm import `com.mykiot.pos.core.network.ApiError`. (`created` chỉ set khi tạo mới — phục vụ luồng auto-chọn từ tab Nhập; khi sửa thì `saved=true` đủ.)

- [ ] **Step 4: Cập nhật `AddSupplierScreen`**

- Thêm tham số: `supplierId: Long? = null` và `onSaved: () -> Unit` (giữ `onCreated` cho luồng cũ từ tab Nhập).
- `LaunchedEffect(supplierId) { supplierId?.let { viewModel.startEdit(it) } ?: viewModel.prefillName(initialName) }`
- Đổi `LaunchedEffect(state.errorMessage){...snackbar...}` → bỏ; thêm `state.error?.let { ErrorDialog(it) { viewModel.clearError() } }`.
- Thêm `LaunchedEffect(state.saved) { if (state.saved) onSaved() }` (cho luồng list). Giữ `LaunchedEffect(state.created){ created -> onCreated(SupplierLite(...)) }` cho luồng tab Nhập (chỉ chạy khi created != null).
- Tiêu đề: `if (state.editingId != null) R.string.cat_supplier_edit else R.string.cat_supplier_add`.

Thêm chuỗi:

```xml
<string name="cat_supplier_edit">Sửa nhà cung cấp</string>
```

> **Lưu ý:** `onCreated` hiện được tab Nhập dùng để auto-chọn NCC vừa tạo. Giữ nguyên tham số đó với giá trị mặc định no-op để không phá call-site cũ: `onCreated: (SupplierLite) -> Unit = {}`.

- [ ] **Step 5: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.supplier.AddSupplierViewModelTest"`
Expected: PASS.

- [ ] **Step 6: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/supplier android/app/src/main/res/values/strings.xml \
        android/app/src/test/java/com/mykiot/pos/feature/supplier/AddSupplierViewModelTest.kt
git commit -m "feat(supplier): AddSupplier hỗ trợ chế độ Sửa (getById + update)"
```

---

### Task 12: Nối Nhà cung cấp vào Routes/Nav/Hub

**Files:**
- Modify: `navigation/Routes.kt`, `navigation/HomeNavHost.kt`, `navigation/HubScreen.kt`

**Interfaces:**
- Consumes: `SupplierListScreen` (Task 10), `AddSupplierScreen` (Task 11).
- Produces: routes `SUPPLIERS`, `SUPPLIER_ADD`, `SUPPLIER_EDIT`; thẻ Hub "Nhà cung cấp" trong nhóm Danh mục.

- [ ] **Step 1: Thêm routes**

Trong `Routes.kt`:

```kotlin
const val SUPPLIERS = "suppliers"
const val SUPPLIER_ADD = "supplier_add"
const val SUPPLIER_EDIT = "supplier_edit/{id}"
fun supplierEdit(id: Long) = "supplier_edit/$id"
```

- [ ] **Step 2: Thêm composable vào `HomeNavHost`**

```kotlin
composable(Routes.SUPPLIERS) { entry ->
    SupplierListScreen(
        onBack = { nav.popOnce(entry) },
        onAdd = { nav.navigateOnce(entry, Routes.SUPPLIER_ADD) },
        onEdit = { nav.navigateOnce(entry, Routes.supplierEdit(it)) },
    )
}
composable(Routes.SUPPLIER_ADD) { entry ->
    AddSupplierScreen(onSaved = { nav.popOnce(entry) }, onCancel = { nav.popOnce(entry) })
}
composable(
    Routes.SUPPLIER_EDIT,
    arguments = listOf(navArgument("id") { type = NavType.LongType }),
) { entry ->
    val id = entry.arguments?.getLong("id") ?: 0L
    AddSupplierScreen(supplierId = id, onSaved = { nav.popOnce(entry) }, onCancel = { nav.popOnce(entry) })
}
```

Thêm import `com.mykiot.pos.feature.supplier.SupplierListScreen` và `com.mykiot.pos.feature.supplier.AddSupplierScreen`.

- [ ] **Step 3: Thêm thẻ Hub**

Trong `HubScreen.kt`, nhóm `core_hub_group_catalog`, thêm item:

```kotlin
HubItem(R.string.core_hub_suppliers, Routes.SUPPLIERS, Icons.Outlined.LocalShipping),
```

Thêm import `androidx.compose.material.icons.outlined.LocalShipping`. Chuỗi:

```xml
<string name="core_hub_suppliers">Nhà cung cấp</string>
```

- [ ] **Step 4: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation android/app/src/main/res/values/strings.xml
git commit -m "feat(supplier): nối Nhà cung cấp vào Hub + điều hướng"
```

---

# PHASE C — Nhóm hàng

### Task 13: CategoryApi + DTO + Repository

**Files:**
- Create: `core/network/CategoryApi.kt`, `core/network/dto/CategoryDtos.kt`, `feature/category/data/CategoryRepository.kt`
- Modify: `core/network/NetworkModule.kt`

**Interfaces:**
- Produces:
  - `CategoryNodeDto(id, name, parentId?, depth, children: List<CategoryNodeDto>)`, `CategoryTreeDto(items)`, `CategoryDto(id, name, parentId?, depth)`, `CategoryCreateDto(name, parentId?)`
  - `CategoryApi.tree(): CategoryTreeDto`, `create(body): CategoryDto`, `update(id, body): CategoryDto`, `delete(id)`
  - `CategoryRepository.tree(): ApiResult<List<CategoryNodeDto>>`, `create/update/delete`

- [ ] **Step 1: Tạo DTO `CategoryDtos.kt`**

```kotlin
package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CategoryNodeDto(
    val id: Long,
    val name: String,
    @SerialName("parent_id") val parentId: Long? = null,
    val depth: Int = 1,
    val children: List<CategoryNodeDto> = emptyList(),
)

@Serializable
data class CategoryTreeDto(val items: List<CategoryNodeDto> = emptyList())

@Serializable
data class CategoryDto(
    val id: Long,
    val name: String,
    @SerialName("parent_id") val parentId: Long? = null,
    val depth: Int = 1,
)

@Serializable
data class CategoryCreateDto(
    val name: String,
    @SerialName("parent_id") val parentId: Long? = null,
)
```

> **Lưu ý khi thực thi:** đối chiếu `CategoryTreeResponse`/`CategoryResponse` ở `backend/modules/product/schemas.py` để khớp đúng tên field (đặc biệt `children` vs cách lồng cây). Điều chỉnh DTO nếu backend dùng tên khác; giữ `@SerialName` cho snake_case.

- [ ] **Step 2: Tạo `CategoryApi.kt`**

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.core.network.dto.CategoryDto
import com.mykiot.pos.core.network.dto.CategoryTreeDto
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PUT
import retrofit2.http.POST
import retrofit2.http.Path

interface CategoryApi {
    @GET("categories") suspend fun tree(): CategoryTreeDto
    @POST("categories") suspend fun create(@Body body: CategoryCreateDto): CategoryDto
    @PUT("categories/{id}") suspend fun update(@Path("id") id: Long, @Body body: CategoryCreateDto): CategoryDto
    @DELETE("categories/{id}") suspend fun delete(@Path("id") id: Long)
}
```

- [ ] **Step 3: Provide trong `NetworkModule`**

```kotlin
@Provides @Singleton
fun categoryApi(retrofit: Retrofit): CategoryApi = retrofit.create(CategoryApi::class.java)
```

- [ ] **Step 4: Tạo `CategoryRepository.kt`**

```kotlin
package com.mykiot.pos.feature.category.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CategoryApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.core.network.dto.CategoryDto
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import javax.inject.Inject

open class CategoryRepository @Inject constructor(
    private val categoryApi: CategoryApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun tree(): ApiResult<List<CategoryNodeDto>> =
        runCatching { categoryApi.tree().items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(body: CategoryCreateDto): ApiResult<CategoryDto> =
        runCatching { categoryApi.create(body) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun update(id: Long, body: CategoryCreateDto): ApiResult<CategoryDto> =
        runCatching { categoryApi.update(id, body) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun delete(id: Long): ApiResult<Unit> =
        runCatching { categoryApi.delete(id) }
            .fold({ ApiResult.Success(Unit) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

- [ ] **Step 5: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/CategoryApi.kt \
        android/app/src/main/java/com/mykiot/pos/core/network/dto/CategoryDtos.kt \
        android/app/src/main/java/com/mykiot/pos/feature/category/data/CategoryRepository.kt \
        android/app/src/main/java/com/mykiot/pos/core/network/NetworkModule.kt
git commit -m "feat(category): CategoryApi + DTO + Repository"
```

---

### Task 14: CategoryViewModel + UiState

**Files:**
- Create: `feature/category/CategoryViewModel.kt`, `feature/category/CategoryUiState.kt`
- Test: `src/test/java/com/mykiot/pos/feature/category/CategoryViewModelTest.kt`

**Interfaces:**
- Consumes: `CategoryRepository` (Task 13).
- Produces: `CategoryUiState(nodes, loading, error, editorOpen, editorParentId, editorEditingId, editorName)`; `CategoryViewModel`: `load()`, `openAdd(parentId: Long?)`, `openEdit(node: CategoryDto-like)`, `onEditorName(v)`, `closeEditor()`, `saveEditor()`, `delete(id)`, `clearError()`.

- [ ] **Step 1: Viết test**

```kotlin
package com.mykiot.pos.feature.category

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.core.network.dto.CategoryDto
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import com.mykiot.pos.feature.category.data.CategoryRepository
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
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class CategoryViewModelTest {
    private val repo = mockk<CategoryRepository>(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load populates nodes`() = runTest {
        coEvery { repo.tree() } returns ApiResult.Success(listOf(CategoryNodeDto(1, "Đồ uống", null, 1)))
        val vm = CategoryViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(1, vm.state.value.nodes.size)
    }

    @Test
    fun `saveEditor add calls create then reloads`() = runTest {
        coEvery { repo.tree() } returns ApiResult.Success(emptyList())
        coEvery { repo.create(any()) } returns ApiResult.Success(CategoryDto(5, "Bánh kẹo", null, 1))
        val vm = CategoryViewModel(repo)
        vm.openAdd(parentId = null)
        vm.onEditorName("Bánh kẹo")
        vm.saveEditor()
        testScheduler.advanceUntilIdle()
        coVerify { repo.create(CategoryCreateDto(name = "Bánh kẹo", parentId = null)) }
    }

    @Test
    fun `delete failure sets error`() = runTest {
        coEvery { repo.tree() } returns ApiResult.Success(emptyList())
        coEvery { repo.delete(3) } returns ApiResult.Failure(ApiError("HAS_PRODUCTS", "Nhóm còn sản phẩm", 400))
        val vm = CategoryViewModel(repo)
        vm.delete(3)
        testScheduler.advanceUntilIdle()
        assertEquals("Nhóm còn sản phẩm", vm.state.value.error?.message)
    }

    @Test
    fun `blank editor name does not call create`() = runTest {
        val vm = CategoryViewModel(repo)
        vm.openAdd(null)
        vm.saveEditor()
        testScheduler.advanceUntilIdle()
        coVerify(exactly = 0) { repo.create(any()) }
        assertTrue(vm.state.value.editorOpen)
    }
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.category.CategoryViewModelTest"`
Expected: FAIL — "unresolved reference: CategoryViewModel".

- [ ] **Step 3: Tạo `CategoryUiState.kt`**

```kotlin
package com.mykiot.pos.feature.category

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.dto.CategoryNodeDto

data class CategoryUiState(
    val nodes: List<CategoryNodeDto> = emptyList(),
    val loading: Boolean = false,
    val error: ApiError? = null,
    val editorOpen: Boolean = false,
    val editorParentId: Long? = null,
    val editorEditingId: Long? = null,
    val editorName: String = "",
)
```

- [ ] **Step 4: Tạo `CategoryViewModel.kt`**

```kotlin
package com.mykiot.pos.feature.category

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.feature.category.data.CategoryRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CategoryViewModel @Inject constructor(
    private val repository: CategoryRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CategoryUiState())
    val state: StateFlow<CategoryUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.tree()) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, nodes = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun openAdd(parentId: Long?) =
        _state.update { it.copy(editorOpen = true, editorParentId = parentId, editorEditingId = null, editorName = "") }

    fun openEdit(id: Long, name: String) =
        _state.update { it.copy(editorOpen = true, editorEditingId = id, editorParentId = null, editorName = name) }

    fun onEditorName(v: String) = _state.update { it.copy(editorName = v) }
    fun closeEditor() = _state.update { it.copy(editorOpen = false, editorName = "") }
    fun clearError() = _state.update { it.copy(error = null) }

    fun saveEditor() {
        val s = _state.value
        if (s.editorName.isBlank()) return
        viewModelScope.launch {
            val body = CategoryCreateDto(name = s.editorName.trim(), parentId = s.editorParentId)
            val editId = s.editorEditingId
            val r = if (editId != null) repository.update(editId, body) else repository.create(body)
            when (r) {
                is ApiResult.Success -> { _state.update { it.copy(editorOpen = false, editorName = "") }; load() }
                is ApiResult.Failure -> _state.update { it.copy(error = r.error) }
            }
        }
    }

    fun delete(id: Long) {
        viewModelScope.launch {
            when (val r = repository.delete(id)) {
                is ApiResult.Success -> load()
                is ApiResult.Failure -> _state.update { it.copy(error = r.error) }
            }
        }
    }
}
```

- [ ] **Step 5: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.category.CategoryViewModelTest"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/category/CategoryViewModel.kt \
        android/app/src/main/java/com/mykiot/pos/feature/category/CategoryUiState.kt \
        android/app/src/test/java/com/mykiot/pos/feature/category/CategoryViewModelTest.kt
git commit -m "feat(category): CategoryViewModel (cây + thêm/sửa/xóa)"
```

---

### Task 15: CategoryTreeScreen

**Files:**
- Create: `feature/category/CategoryTreeScreen.kt`
- Modify: `res/values/strings.xml`

**Interfaces:**
- Consumes: `CategoryViewModel` (Task 14), `ErrorDialog`, `ConfirmDialog`, `AppTextField`, `AppHeader`.
- Produces: `@Composable fun CategoryTreeScreen(onBack, viewModel = hiltViewModel())`.

- [ ] **Step 1: Thêm chuỗi**

```xml
<string name="core_hub_categories">Nhóm hàng</string>
<string name="cat_category_title">Nhóm hàng</string>
<string name="cat_category_empty">Chưa có nhóm hàng</string>
<string name="cat_category_add_root">Thêm nhóm</string>
<string name="cat_category_add_child">Thêm nhóm con</string>
<string name="cat_category_edit">Sửa nhóm</string>
<string name="cat_category_name_label">Tên nhóm</string>
<string name="cat_category_delete_confirm">Xóa nhóm này?</string>
```

- [ ] **Step 2: Tạo `CategoryTreeScreen.kt`**

```kotlin
package com.mykiot.pos.feature.category

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.ConfirmDialog
import com.mykiot.pos.core.ui.ErrorDialog

@Composable
fun CategoryTreeScreen(
    onBack: () -> Unit,
    viewModel: CategoryViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var deleteId by remember { mutableStateOf<Long?>(null) }
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = stringResource(R.string.cat_category_title),
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
                actions = {
                    TextButton(onClick = { viewModel.openAdd(null) }) { Text(stringResource(R.string.cat_category_add_root)) }
                },
            )
        },
    ) { padding ->
        if (state.nodes.isEmpty()) {
            Column(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(stringResource(R.string.cat_category_empty), Modifier.padding(top = 48.dp))
            }
        } else {
            LazyColumn(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
                items(state.nodes, key = { it.id }) { parent ->
                    CategoryRow(parent, indent = 0, viewModel = viewModel, onAskDelete = { deleteId = it })
                    parent.children.forEach { child ->
                        CategoryRow(child, indent = 16, viewModel = viewModel, onAskDelete = { deleteId = it })
                    }
                }
            }
        }
    }

    if (state.editorOpen) {
        AlertDialog(
            onDismissRequest = viewModel::closeEditor,
            title = {
                Text(
                    stringResource(
                        if (state.editorEditingId != null) R.string.cat_category_edit
                        else if (state.editorParentId != null) R.string.cat_category_add_child
                        else R.string.cat_category_add_root,
                    ),
                )
            },
            text = {
                AppTextField(
                    value = state.editorName,
                    onValueChange = viewModel::onEditorName,
                    label = stringResource(R.string.cat_category_name_label),
                    modifier = Modifier.fillMaxWidth(),
                )
            },
            confirmButton = { TextButton(onClick = viewModel::saveEditor) { Text(stringResource(R.string.common_save)) } },
            dismissButton = { TextButton(onClick = viewModel::closeEditor) { Text(stringResource(R.string.common_cancel)) } },
        )
    }

    deleteId?.let { id ->
        ConfirmDialog(
            title = stringResource(R.string.cat_category_title),
            message = stringResource(R.string.cat_category_delete_confirm),
            onConfirm = { viewModel.delete(id) },
            onDismiss = { deleteId = null },
        )
    }

    state.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun CategoryRow(
    node: CategoryNodeDto,
    indent: Int,
    viewModel: CategoryViewModel,
    onAskDelete: (Long) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(start = indent.dp, top = 6.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(node.name, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        if (node.depth == 1) {
            IconButton(onClick = { viewModel.openAdd(node.id) }) {
                Icon(Icons.Outlined.Add, contentDescription = stringResource(R.string.cat_category_add_child))
            }
        }
        IconButton(onClick = { viewModel.openEdit(node.id, node.name) }) {
            Icon(Icons.Outlined.Edit, contentDescription = stringResource(R.string.cat_category_edit))
        }
        IconButton(onClick = { onAskDelete(node.id) }) {
            Icon(Icons.Outlined.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error)
        }
    }
}
```

> Cần chuỗi `common_save` (kiểm tra đã có chưa; nếu chưa, thêm `<string name="common_save">Lưu</string>`).

- [ ] **Step 3: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/category/CategoryTreeScreen.kt \
        android/app/src/main/res/values/strings.xml
git commit -m "feat(category): CategoryTreeScreen (cây 2 cấp, thêm/sửa/xóa)"
```

---

### Task 16: Nối Nhóm hàng vào Routes/Nav/Hub

**Files:**
- Modify: `navigation/Routes.kt`, `navigation/HomeNavHost.kt`, `navigation/HubScreen.kt`

- [ ] **Step 1: Route**

`Routes.kt`: `const val CATEGORIES = "categories"`

- [ ] **Step 2: Composable trong `HomeNavHost`**

```kotlin
composable(Routes.CATEGORIES) { entry ->
    CategoryTreeScreen(onBack = { nav.popOnce(entry) })
}
```

Import `com.mykiot.pos.feature.category.CategoryTreeScreen`.

- [ ] **Step 3: Thẻ Hub nhóm Danh mục**

```kotlin
HubItem(R.string.core_hub_categories, Routes.CATEGORIES, Icons.Outlined.Category),
```

Import `androidx.compose.material.icons.outlined.Category`.

- [ ] **Step 4: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation
git commit -m "feat(category): nối Nhóm hàng vào Hub + điều hướng"
```

---

# PHASE D — Lịch sử phiếu nhập

### Task 17: API + DTO + Repository cho danh sách phiếu nhập

**Files:**
- Modify: `core/network/dto/InventoryDtos.kt`, `core/network/InventoryApi.kt`, `feature/receipt/data/ReceiptRepository.kt`

**Interfaces:**
- Produces:
  - `GoodsReceiptBriefDto(id, code, supplierId?, supplierName?, total, paidAmount, status, completedAt?, createdAt)`
  - `GoodsReceiptListDto(items, pagination: PaginationDto?)`
  - `InventoryApi.listReceipts(page, limit): GoodsReceiptListDto`
  - `ReceiptRepository.listReceipts(page): ApiResult<PageResult<GoodsReceiptBriefDto>>`

- [ ] **Step 1: Thêm DTO vào `InventoryDtos.kt`**

```kotlin
@Serializable
data class GoodsReceiptBriefDto(
    val id: Long,
    val code: String,
    @SerialName("supplier_id") val supplierId: Long? = null,
    @SerialName("supplier_name") val supplierName: String? = null,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class GoodsReceiptListDto(
    val items: List<GoodsReceiptBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)
```

- [ ] **Step 2: Thêm method vào `InventoryApi`**

```kotlin
@GET("goods-receipts")
suspend fun listReceipts(
    @Query("page") page: Int = 1,
    @Query("limit") limit: Int = 20,
): GoodsReceiptListDto
```

Import `GoodsReceiptListDto`.

- [ ] **Step 3: Thêm vào `ReceiptRepository`**

```kotlin
open suspend fun listReceipts(page: Int = 1): ApiResult<PageResult<GoodsReceiptBriefDto>> =
    runCatching {
        val r = inventoryApi.listReceipts(page = page)
        PageResult.from(r.items, r.pagination)
    }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
```

Thêm import `PageResult`, `GoodsReceiptBriefDto`. (Kiểm tra `ReceiptRepository` đã inject `inventoryApi` + `errorMapper`; nếu chưa có `errorMapper`, thêm vào constructor.)

- [ ] **Step 4: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/dto/InventoryDtos.kt \
        android/app/src/main/java/com/mykiot/pos/core/network/InventoryApi.kt \
        android/app/src/main/java/com/mykiot/pos/feature/receipt/data/ReceiptRepository.kt
git commit -m "feat(receipt): API + repo danh sách phiếu nhập (phân trang)"
```

---

### Task 18: GoodsReceiptListViewModel

**Files:**
- Create: `feature/receipt/GoodsReceiptListViewModel.kt`
- Test: `src/test/java/com/mykiot/pos/feature/receipt/GoodsReceiptListViewModelTest.kt`

**Interfaces:**
- Consumes: `ReceiptRepository.listReceipts` (Task 17).
- Produces: `GoodsReceiptListViewModel : PagingListViewModel<GoodsReceiptBriefDto>` với `load()`.

- [ ] **Step 1: Viết test**

```kotlin
package com.mykiot.pos.feature.receipt

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.GoodsReceiptBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.feature.receipt.data.ReceiptRepository
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

class GoodsReceiptListViewModelTest {
    private val repo = mockk<ReceiptRepository>()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load populates receipts`() = runTest {
        coEvery { repo.listReceipts(any()) } returns ApiResult.Success(
            PageResult(
                listOf(GoodsReceiptBriefDto(1, "NK20260620-001", null, "NCC A", "100000", "100000", "COMPLETED", null, "2026-06-20T01:00:00Z")),
                1, 1,
            ),
        )
        val vm = GoodsReceiptListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals("NK20260620-001", vm.paging.value.items.first().code)
    }

    @Test
    fun `load sets error on failure`() = runTest {
        coEvery { repo.listReceipts(any()) } returns ApiResult.Failure(ApiError("X", "Lỗi tải phiếu nhập"))
        val vm = GoodsReceiptListViewModel(repo)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals("Lỗi tải phiếu nhập", vm.paging.value.error?.message)
    }
}
```

- [ ] **Step 2: Chạy test — kỳ vọng FAIL**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.receipt.GoodsReceiptListViewModelTest"`
Expected: FAIL.

- [ ] **Step 3: Tạo VM**

```kotlin
package com.mykiot.pos.feature.receipt

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.GoodsReceiptBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
import com.mykiot.pos.feature.receipt.data.ReceiptRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class GoodsReceiptListViewModel @Inject constructor(
    private val repository: ReceiptRepository,
) : PagingListViewModel<GoodsReceiptBriefDto>() {
    fun load() = refresh()
    override suspend fun fetch(page: Int): ApiResult<PageResult<GoodsReceiptBriefDto>> =
        repository.listReceipts(page)
}
```

- [ ] **Step 4: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.receipt.GoodsReceiptListViewModelTest"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/receipt/GoodsReceiptListViewModel.kt \
        android/app/src/test/java/com/mykiot/pos/feature/receipt/GoodsReceiptListViewModelTest.kt
git commit -m "feat(receipt): GoodsReceiptListViewModel"
```

---

### Task 19: GoodsReceiptListScreen

**Files:**
- Create: `feature/receipt/GoodsReceiptListScreen.kt`
- Modify: `res/values/strings.xml`

**Interfaces:**
- Consumes: `GoodsReceiptListViewModel` (Task 18), `PagedLazyColumn`, `ErrorDialog`, `Money.formatVnd/formatDateTime`.
- Produces: `@Composable fun GoodsReceiptListScreen(onBack, onOpenDetail: (Long) -> Unit, viewModel = hiltViewModel())`.

- [ ] **Step 1: Chuỗi**

```xml
<string name="core_hub_receipt_history">Lịch sử nhập</string>
<string name="receipt_history_title">Lịch sử phiếu nhập</string>
<string name="receipt_history_empty">Chưa có phiếu nhập</string>
<string name="receipt_status_completed">Đã hoàn tất</string>
<string name="receipt_status_draft">Nháp</string>
<string name="receipt_status_cancelled">Đã hủy</string>
<string name="receipt_supplier_walkin">Không có NCC</string>
```

- [ ] **Step 2: Tạo `GoodsReceiptListScreen.kt`**

```kotlin
package com.mykiot.pos.feature.receipt

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.GoodsReceiptBriefDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

@Composable
fun GoodsReceiptListScreen(
    onBack: () -> Unit,
    onOpenDetail: (Long) -> Unit,
    viewModel: GoodsReceiptListViewModel = hiltViewModel(),
) {
    val paging by viewModel.paging.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = { AppHeader(title = stringResource(R.string.receipt_history_title), onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
    ) { padding ->
        Column(Modifier.padding(padding).padding(horizontal = 16.dp)) {
            PagedLazyColumn(
                state = paging,
                onLoadMore = viewModel::loadMore,
                emptyText = stringResource(R.string.receipt_history_empty),
                key = { it.id },
            ) { r -> ReceiptRow(r, onClick = { onOpenDetail(r.id) }) }
        }
    }

    paging.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun ReceiptRow(r: GoodsReceiptBriefDto, onClick: () -> Unit) {
    val statusText = when (r.status) {
        "COMPLETED" -> stringResource(R.string.receipt_status_completed)
        "CANCELLED" -> stringResource(R.string.receipt_status_cancelled)
        else -> stringResource(R.string.receipt_status_draft)
    }
    Surface(onClick = onClick, color = MaterialTheme.colorScheme.surface, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.fillMaxWidth().padding(14.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(r.code, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Text(statusText, style = MaterialTheme.typography.labelMedium)
            }
            Text(r.supplierName ?: stringResource(R.string.receipt_supplier_walkin), style = MaterialTheme.typography.bodySmall)
            Row(Modifier.fillMaxWidth()) {
                Text(formatVnd(r.total), style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                Text(formatDateTime(r.completedAt ?: r.createdAt), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
```

> Khớp đúng chữ ký `PagedLazyColumn` như Task 10.

- [ ] **Step 3: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/receipt/GoodsReceiptListScreen.kt \
        android/app/src/main/res/values/strings.xml
git commit -m "feat(receipt): GoodsReceiptListScreen"
```

---

### Task 20: Nối Lịch sử nhập vào Routes/Nav/Hub

**Files:**
- Modify: `navigation/Routes.kt`, `navigation/HomeNavHost.kt`, `navigation/HubScreen.kt`

- [ ] **Step 1: Route**

`Routes.kt`: `const val RECEIPT_HISTORY = "receipt_history"`

- [ ] **Step 2: Composable**

```kotlin
composable(Routes.RECEIPT_HISTORY) { entry ->
    GoodsReceiptListScreen(
        onBack = { nav.popOnce(entry) },
        onOpenDetail = { nav.navigateOnce(entry, Routes.receiptDetail(it)) },
    )
}
```

Import `com.mykiot.pos.feature.receipt.GoodsReceiptListScreen`. (`Routes.receiptDetail` đã tồn tại.)

- [ ] **Step 3: Thẻ Hub nhóm Kho**

Trong `core_hub_group_inventory`, thêm sau Tồn kho:

```kotlin
HubItem(R.string.core_hub_receipt_history, Routes.RECEIPT_HISTORY, Icons.Outlined.History),
```

Import `androidx.compose.material.icons.outlined.History`.

- [ ] **Step 4: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/navigation
git commit -m "feat(receipt): nối Lịch sử nhập vào Hub + điều hướng"
```

---

# PHASE E — Tồn kho + tab "Sắp hết"

### Task 21: InventoryViewModel + UiState — tab low-stock

**Files:**
- Modify: `feature/inventory/InventoryViewModel.kt`, `feature/inventory/InventoryUiState.kt`
- Test: `src/test/java/com/mykiot/pos/feature/inventory/InventoryViewModelTest.kt` (mở rộng)

**Interfaces:**
- Consumes: `InventoryRepository.lowStock()` (đã có — kiểm tra; nếu chưa, thêm `open suspend fun lowStock(): ApiResult<List<InventoryItemDto>>` gọi `inventoryApi.lowStock().items`).
- Produces: `InventoryViewModel`: `val tab: StateFlow<InventoryTab>`, `selectTab(tab)`, `val lowStock: StateFlow<LowStockState>`. `enum class InventoryTab { ALL, LOW }`.

- [ ] **Step 1: Đảm bảo repository có `lowStock()`**

Kiểm tra `feature/inventory/data/InventoryRepository.kt`. Nếu thiếu, thêm:

```kotlin
open suspend fun lowStock(): ApiResult<List<InventoryItemDto>> =
    runCatching { inventoryApi.lowStock().items }
        .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
```

- [ ] **Step 2: Viết test mở rộng**

Thêm vào `InventoryViewModelTest.kt`:

```kotlin
@Test
fun `selectTab LOW loads low stock items`() = runTest {
    coEvery { repo.list(any(), any()) } returns ApiResult.Success(PageResult(emptyList(), 1, 1))
    coEvery { repo.lowStock() } returns ApiResult.Success(
        listOf(InventoryItemDto(productId = 1, productSku = "SP1", productName = "Mì gói", unit = "gói", quantity = "2", minStock = 5, salePrice = "5000")),
    )
    val vm = InventoryViewModel(repo)
    vm.selectTab(InventoryTab.LOW)
    testScheduler.advanceUntilIdle()
    assertEquals(InventoryTab.LOW, vm.tab.value)
    assertEquals(1, vm.lowStock.value.items.size)
}
```

(Thêm import `InventoryItemDto`, `PageResult`, `InventoryTab` nếu cần.)

- [ ] **Step 3: Chạy test — kỳ vọng FAIL**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.inventory.InventoryViewModelTest"`
Expected: FAIL — "unresolved reference: selectTab/InventoryTab".

- [ ] **Step 4: Cập nhật `InventoryUiState.kt`**

Thêm:

```kotlin
enum class InventoryTab { ALL, LOW }

data class LowStockState(
    val items: List<InventoryItemDto> = emptyList(),
    val loading: Boolean = false,
    val error: com.mykiot.pos.core.network.ApiError? = null,
)
```

- [ ] **Step 5: Cập nhật `InventoryViewModel.kt`**

Thêm vào VM:

```kotlin
private val _tab = MutableStateFlow(InventoryTab.ALL)
val tab: StateFlow<InventoryTab> = _tab.asStateFlow()

private val _lowStock = MutableStateFlow(LowStockState())
val lowStock: StateFlow<LowStockState> = _lowStock.asStateFlow()

fun selectTab(tab: InventoryTab) {
    _tab.value = tab
    if (tab == InventoryTab.LOW && _lowStock.value.items.isEmpty()) loadLowStock()
}

fun loadLowStock() {
    _lowStock.update { it.copy(loading = true, error = null) }
    viewModelScope.launch {
        when (val r = repository.lowStock()) {
            is ApiResult.Success -> _lowStock.update { it.copy(loading = false, items = r.data) }
            is ApiResult.Failure -> _lowStock.update { it.copy(loading = false, error = r.error) }
        }
    }
}

fun clearLowStockError() = _lowStock.update { it.copy(error = null) }
```

- [ ] **Step 6: Chạy test — kỳ vọng PASS**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mykiot.pos.feature.inventory.InventoryViewModelTest"`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/inventory/InventoryViewModel.kt \
        android/app/src/main/java/com/mykiot/pos/feature/inventory/InventoryUiState.kt \
        android/app/src/main/java/com/mykiot/pos/feature/inventory/data/InventoryRepository.kt \
        android/app/src/test/java/com/mykiot/pos/feature/inventory/InventoryViewModelTest.kt
git commit -m "feat(inventory): VM hỗ trợ tab Tất cả / Sắp hết"
```

---

### Task 22: InventoryScreen — TabRow Tất cả / Sắp hết

**Files:**
- Modify: `feature/inventory/InventoryScreen.kt`
- Modify: `res/values/strings.xml`

**Interfaces:**
- Consumes: `InventoryViewModel.tab/selectTab/lowStock` (Task 21), `ErrorDialog`.

- [ ] **Step 1: Chuỗi**

```xml
<string name="inventory_tab_all">Tất cả</string>
<string name="inventory_tab_low">Sắp hết</string>
<string name="inventory_low_empty">Không có hàng sắp hết</string>
```

- [ ] **Step 2: Thêm TabRow + nhánh nội dung**

Trong `InventoryScreen`, đọc thêm:

```kotlin
val tab by viewModel.tab.collectAsStateWithLifecycle()
val lowStock by viewModel.lowStock.collectAsStateWithLifecycle()
```

Phía trên danh sách, thêm:

```kotlin
androidx.compose.material3.TabRow(selectedTabIndex = tab.ordinal) {
    androidx.compose.material3.Tab(
        selected = tab == InventoryTab.ALL,
        onClick = { viewModel.selectTab(InventoryTab.ALL) },
        text = { androidx.compose.material3.Text(stringResource(R.string.inventory_tab_all)) },
    )
    androidx.compose.material3.Tab(
        selected = tab == InventoryTab.LOW,
        onClick = { viewModel.selectTab(InventoryTab.LOW) },
        text = { androidx.compose.material3.Text(stringResource(R.string.inventory_tab_low)) },
    )
}
```

- Khi `tab == InventoryTab.ALL`: giữ nguyên list phân trang + ô tìm kiếm hiện có.
- Khi `tab == InventoryTab.LOW`: hiển thị `lowStock.items` bằng `LazyColumn` dùng cùng row item hiện có; nếu rỗng (và không loading) hiện `inventory_low_empty`.
- Thêm `lowStock.error?.let { ErrorDialog(it) { viewModel.clearLowStockError() } }`.

> Tái dùng composable row tồn kho hiện có trong file; chỉ đổi nguồn dữ liệu theo tab. Giữ `MovementsDialog` (kardex) hoạt động ở cả hai tab khi bấm vào item.

- [ ] **Step 3: assembleDebug**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Test toàn bộ**

Run: `cd android && ./gradlew :app:testDebugUnitTest`
Expected: BUILD SUCCESSFUL, tất cả test xanh.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/inventory/InventoryScreen.kt \
        android/app/src/main/res/values/strings.xml
git commit -m "feat(inventory): tab Tất cả / Sắp hết trong màn Tồn kho"
```

---

## Self-Review

**Spec coverage:**
- Foundation §1 SessionManager + persist role → Tasks 1–3. ✅
- Foundation §2 role-gating Hub → Task 7. ✅
- Foundation §3 ErrorDialog + migrate 10 màn → Tasks 4–6. ✅
- Foundation §4 token_version (SP-4) → ngoài phạm vi SP-1 (đã ghi rõ). ✅
- F1 Nhà cung cấp (list + thêm/sửa) → Tasks 8–12. ✅
- F2 Nhóm hàng (cây CRUD) → Tasks 13–16. ✅
- F3 Lịch sử phiếu nhập (thẻ Hub riêng) → Tasks 17–20. ✅
- F4 Tồn kho + tab Sắp hết → Tasks 21–22. ✅
- Hub IA (3 thẻ mới + nhóm) → Tasks 12, 16, 20. ✅
- i18n + test ViewModel + build xanh → rải khắp các task. ✅

**Placeholder scan:** Không có "TBD/TODO". Các "Lưu ý khi thực thi" yêu cầu đối chiếu chữ ký `PagedLazyColumn`/schema backend là chỉ dẫn xác minh, không phải nội dung bỏ ngỏ — code mẫu vẫn đầy đủ.

**Type consistency:**
- `PagingState.error: ApiError?` dùng nhất quán ở Task 5 và mọi VM/test paging sau đó (`error?.message`).
- `SupplierCreateDto` dùng cho cả create và update (Task 8, 11).
- `errorIconKind`/`ErrorIconKind` (Task 4) dùng trong `ErrorDialog`.
- `SessionManager.set/clear/restore/current/isOwner` (Task 2) dùng ở Task 3, 7.
- `InventoryTab`/`LowStockState` (Task 21) dùng ở Task 22.

Lưu ý phụ thuộc: Task 5 đổi `PagingState`; Tasks 9/18 (paging VM mới) phụ thuộc Task 5 đã xong (đọc `error`). Thực thi theo thứ tự task.
