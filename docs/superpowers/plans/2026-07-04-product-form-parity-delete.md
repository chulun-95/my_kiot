# Product Form Parity (App ↔ Web) + Delete Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Android "Thêm sản phẩm" screen to parity with web (nhóm hàng, tồn tối thiểu, trạng thái), enforce required fields (đơn vị/giá vốn/giá bán) on create, add a Sửa SP screen on Android, and add a working Xóa SP feature on Android (web already has it) — with the backend delete endpoint correctly restricted to OWNER.

**Architecture:** Backend already exposes everything needed (`ProductResponse` has `category_id`/`min_stock`/`status`; `DELETE /products/{id}` soft-deletes) except a missing OWNER role guard on delete. Web only needs two `required` attributes added. Android needs: new DTO/API/repository methods (`update`, `delete`, richer `ProductBriefDto`), an extended `AddProductViewModel`/`AddProductScreen` that handles both create and edit (mirroring the existing `AddSupplierScreen`/`AddSupplierViewModel` create-or-edit pattern), a new `PRODUCT_EDIT` route, and edit/delete buttons on `ProductDetailScreen`.

**Tech Stack:** FastAPI/SQLAlchemy/Pydantic (backend), React/TypeScript (web), Kotlin/Jetpack Compose/Hilt/Retrofit/kotlinx.serialization/MockK (Android).

## Global Constraints

- Mọi message lỗi/validation hiển thị cho người dùng phải là tiếng Việt (CLAUDE.md).
- Mọi query/mutation phải tôn trọng `tenant_id` — không đổi trong plan này (không chạm query mới).
- Phân quyền: "Xóa SP: OWNER ✅ CASHIER ❌", "Tạo/sửa SP: OWNER ✅ CASHIER ✅", "Xem giá vốn: OWNER ✅, CASHIER ⚠️ theo `tenant.settings.show_cost_to_cashier`" (CLAUDE.md bảng phân quyền).
- Giữ nguyên hành vi nút xóa hiện tại (soft-delete thật, ẩn hẳn, không phục hồi) — không tách thành khái niệm "tạm ngừng bán" riêng (quyết định đã chốt trong spec).
- Không đổi schema bắt buộc ở backend — validate "bắt buộc nhập đủ" chỉ ở tầng client.
- Giá vốn bắt buộc khi tạo/sửa SP: chỉ với OWNER; Cashier giữ optional (mặc định 0), vì field này ẩn với Cashier.

Spec: `docs/superpowers/specs/2026-07-04-product-form-parity-delete-design.md`

---

### Task 1: Backend — giới hạn OWNER cho DELETE /products/{id}

**Files:**
- Modify: `backend/modules/product/router.py:251-260`
- Test: `tests/test_product.py`

**Interfaces:**
- Consumes: `require_role` từ `backend/dependencies.py:55` (đã import sẵn ở `router.py:8`).
- Produces: không đổi response shape, chỉ thêm 403 cho role không phải OWNER.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/test_product.py` (sau `test_delete_product_soft`, dùng đúng pattern tạo Cashier đã có ở `tests/test_product_units.py::test_cashier_cannot_create_unit`):

```python
@pytest.mark.asyncio
async def test_delete_product_requires_owner(client, registered_owner):
    """CASHIER role must get 403 on DELETE /products/{id}."""
    h_owner = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "Bia", "unit": "lon", "sale_price": 10000,
    }, headers=h_owner)).json()

    cashier_resp = await client.post("/api/v1/staff", json={
        "full_name": "Cashier Test",
        "phone": "0987654321",
        "password": "secret123",
        "role": "CASHIER",
    }, headers=h_owner)
    assert cashier_resp.status_code == 201, cashier_resp.text

    login = await client.post("/api/v1/auth/login", json={
        "phone": "0987654321",
        "password": "secret123",
    })
    h_cashier = _auth(login.json()["access_token"])

    r = await client.delete(f"/api/v1/products/{p['id']}", headers=h_cashier)
    assert r.status_code == 403

    # SP vẫn còn nguyên (chưa bị xóa)
    r2 = await client.get(f"/api/v1/products/{p['id']}", headers=h_owner)
    assert r2.status_code == 200
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `.venv/Scripts/python.exe -m pytest tests/test_product.py::test_delete_product_requires_owner -v`
Expected: FAIL — `assert 200 == 403` (Cashier hiện xóa được vì route chưa giới hạn role).

- [ ] **Step 3: Thêm role guard vào route**

Trong `backend/modules/product/router.py`, sửa decorator của `delete_product` (dòng 251-260):

```python
@product_router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("OWNER"))],
)
async def delete_product(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    product_id: int = Path(..., ge=1),
):
    await product_service.soft_delete_product(
        db, user.current_tenant_id, user.id, product_id
    )
    return MessageResponse(message="Đã ngừng bán sản phẩm")
```

- [ ] **Step 4: Chạy lại toàn bộ test_product.py, xác nhận PASS**

Run: `.venv/Scripts/python.exe -m pytest tests/test_product.py -v`
Expected: PASS toàn bộ, bao gồm `test_delete_product_soft` (dùng OWNER, không bị ảnh hưởng) và `test_delete_product_requires_owner` mới.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/product/router.py tests/test_product.py
git commit -m "fix(product): giới hạn xóa sản phẩm cho OWNER, khớp bảng phân quyền"
```

---

### Task 2: Web — bắt buộc nhập Đơn vị + Giá vốn (OWNER) khi tạo/sửa SP

**Files:**
- Modify: `frontend/src/pages/products/ProductForm.tsx:198-223`

**Interfaces:**
- Consumes: `viValidity` từ `frontend/src/utils/validity.ts` (đã import sẵn ở đầu file).
- Produces: không đổi API payload — chỉ thêm ràng buộc HTML5 phía client.

- [ ] **Step 1: Thêm `required` cho input Đơn vị**

Trong `frontend/src/pages/products/ProductForm.tsx`, sửa khối input "Đơn vị" (dòng 198-209):

```tsx
          <label className="block">
            <span className="text-sm text-slate-700">Đơn vị *</span>
            <FieldHint text="Đơn vị tính khi bán: cái, gói, chai, lon, kg, lít, thùng... Hiển thị trên giỏ hàng POS và bill in." />
            <input
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              required
              maxLength={30}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
              {...viValidity({
                valueMissing: 'Vui lòng nhập đơn vị tính',
                tooLong: 'Đơn vị tối đa 30 ký tự',
              })}
            />
          </label>
```

- [ ] **Step 2: Thêm `required` cho input Giá vốn (nhánh OWNER)**

Sửa khối "Giá vốn" (dòng 210-223):

```tsx
          {isOwner && (
            <label className="block">
              <span className="text-sm text-slate-700">Giá vốn *</span>
              <FieldHint text="Giá nhập trung bình (bình quân gia quyền) — dùng để tính lợi nhuận. Hệ thống tự cập nhật mỗi lần nhập kho. Cashier không thấy giá vốn." />
              <div className="mt-1">
                <MoneyInput
                  value={costPrice}
                  onChange={(v) => setCostPrice(String(v))}
                  className="w-full px-3 py-2 border border-slate-300 rounded"
                  aria-label="Giá vốn"
                  required
                />
              </div>
            </label>
          )}
```

- [ ] **Step 3: Xác nhận build/typecheck pass**

Run: `cd frontend && npm run build`
Expected: build thành công, không lỗi TypeScript (props `required` đã có sẵn trong `MoneyInput`'s `Props` type qua `InputHTMLAttributes`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/products/ProductForm.tsx
git commit -m "feat(product): bắt buộc nhập đơn vị + giá vốn (owner) khi tạo/sửa SP"
```

---

### Task 3: Android — data layer (DTO/API/Repository) cho update + delete

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/dto/ProductDtos.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/core/network/ProductApi.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/data/ProductRepository.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/data/ProductListRepository.kt`

**Interfaces:**
- Produces: `ProductBriefDto` với 3 field mới (`categoryId: Long?`, `minStock: Int`, `description: String?`); `ProductCreateDto` với `categoryId: Long?` mới; `ProductUpdateDto` (mới, `costPrice: String?` nullable — để Cashier sửa SP không vô tình ghi đè giá vốn ẩn); `ProductApi.update(id, ProductUpdateDto): ProductBriefDto`; `ProductApi.delete(id)`; `ProductRepository.get(id): ApiResult<ProductBriefDto>`; `ProductRepository.update(id, ProductUpdateDto): ApiResult<ProductBriefDto>`; `ProductListRepository.delete(id): ApiResult<Unit>`. Dùng ở Task 4 và Task 6.

- [ ] **Step 1: Cập nhật `ProductDtos.kt`**

Thay toàn bộ nội dung `android/app/src/main/java/com/mykiot/pos/core/network/dto/ProductDtos.kt`:

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
    @SerialName("min_stock") val minStock: Int = 0,
    @SerialName("category_id") val categoryId: Long? = null,
    val description: String? = null,
    @SerialName("image_url") val imageUrl: String? = null,
    @SerialName("allow_negative") val allowNegative: Boolean = false,
    val status: String,
    val units: List<ProductUnitDto> = emptyList(),
    @SerialName("matched_unit") val matchedUnit: ProductUnitDto? = null,
    @SerialName("stock_status") val stockStatus: String? = null,
)

@Serializable
data class ProductSearchDto(val items: List<ProductBriefDto> = emptyList())

@Serializable
data class ProductListDto(
    val items: List<ProductBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

/** Body tạo SP mới (POST /products). Tiền gửi dạng chuỗi để tránh sai số float. */
@Serializable
data class ProductCreateDto(
    val name: String,
    val sku: String? = null,
    val barcode: String? = null,
    @SerialName("category_id") val categoryId: Long? = null,
    val unit: String = "cái",
    @SerialName("cost_price") val costPrice: String = "0",
    @SerialName("sale_price") val salePrice: String = "0",
    @SerialName("min_stock") val minStock: Int = 0,
    val status: String = "ACTIVE",
    @SerialName("allow_negative") val allowNegative: Boolean = false,
)

/**
 * Body sửa SP (PUT /products/{id}). [costPrice] nullable riêng với [ProductCreateDto] —
 * nếu Cashier sửa SP (form ẩn field giá vốn) thì gửi null để KHÔNG ghi đè giá vốn hiện
 * có (backend bỏ qua field null khi update, xem `update_product` trong service.py).
 */
@Serializable
data class ProductUpdateDto(
    val name: String,
    val sku: String? = null,
    val barcode: String? = null,
    @SerialName("category_id") val categoryId: Long? = null,
    val unit: String = "cái",
    @SerialName("cost_price") val costPrice: String? = null,
    @SerialName("sale_price") val salePrice: String = "0",
    @SerialName("min_stock") val minStock: Int = 0,
    val status: String = "ACTIVE",
)
```

- [ ] **Step 2: Cập nhật `ProductApi.kt`**

Thay toàn bộ nội dung `android/app/src/main/java/com/mykiot/pos/core/network/ProductApi.kt`:

```kotlin
package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.core.network.dto.ProductListDto
import com.mykiot.pos.core.network.dto.ProductSearchDto
import com.mykiot.pos.core.network.dto.ProductUpdateDto
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface ProductApi {
    @GET("products")
    suspend fun list(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): ProductListDto

    @GET("products/{id}") suspend fun get(@Path("id") id: Long): ProductBriefDto
    @GET("products/search") suspend fun search(@Query("q") q: String): ProductSearchDto
    @GET("products/barcode/{code}") suspend fun byBarcode(@Path("code") code: String): ProductBriefDto

    @POST("products") suspend fun create(@Body body: ProductCreateDto): ProductBriefDto
    @PUT("products/{id}") suspend fun update(@Path("id") id: Long, @Body body: ProductUpdateDto): ProductBriefDto
    @DELETE("products/{id}") suspend fun delete(@Path("id") id: Long)
}
```

- [ ] **Step 3: Cập nhật `ProductRepository.kt`**

Thay toàn bộ nội dung `android/app/src/main/java/com/mykiot/pos/feature/product/data/ProductRepository.kt`:

```kotlin
package com.mykiot.pos.feature.product.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.core.network.dto.ProductUpdateDto
import javax.inject.Inject

open class ProductRepository @Inject constructor(
    private val productApi: ProductApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun get(id: Long): ApiResult<ProductBriefDto> =
        runCatching { productApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(dto: ProductCreateDto): ApiResult<ProductBriefDto> =
        runCatching { productApi.create(dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun update(id: Long, dto: ProductUpdateDto): ApiResult<ProductBriefDto> =
        runCatching { productApi.update(id, dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

- [ ] **Step 4: Cập nhật `ProductListRepository.kt`**

Thay toàn bộ nội dung `android/app/src/main/java/com/mykiot/pos/feature/product/data/ProductListRepository.kt`:

```kotlin
package com.mykiot.pos.feature.product.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
import javax.inject.Inject

open class ProductListRepository @Inject constructor(
    private val productApi: ProductApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?, page: Int = 1): ApiResult<PageResult<ProductBriefDto>> =
        runCatching {
            val r = productApi.list(search = search.takeIf { !it.isNullOrBlank() }, page = page)
            PageResult.from(r.items, r.pagination)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun get(id: Long): ApiResult<ProductBriefDto> =
        runCatching { productApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun delete(id: Long): ApiResult<Unit> =
        runCatching { productApi.delete(id) }
            .fold({ ApiResult.Success(Unit) }, { ApiResult.Failure(errorMapper.map(it)) })
}
```

- [ ] **Step 5: Biên dịch để xác nhận không lỗi**

Run: `cd android && ./gradlew compileDebugKotlin`
Expected: BUILD SUCCESSFUL (không có test nào phụ thuộc các file này thay đổi hành vi — `ProductBriefDto`/`ProductCreateDto` chỉ thêm field có default, các constructor dùng named-arg hiện có trong `ProductListViewModelTest.kt`/`ReceiptViewModelTest.kt`/`PosViewModelTest.kt`/`ProductDetailViewModelTest.kt` không bị phá).

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/core/network/dto/ProductDtos.kt \
        android/app/src/main/java/com/mykiot/pos/core/network/ProductApi.kt \
        android/app/src/main/java/com/mykiot/pos/feature/product/data/ProductRepository.kt \
        android/app/src/main/java/com/mykiot/pos/feature/product/data/ProductListRepository.kt
git commit -m "feat(android): thêm API/DTO update + delete sản phẩm"
```

---

### Task 4: Android — mở rộng `AddProductViewModel` (chế độ Sửa + validate bắt buộc + nhóm hàng)

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/AddProductViewModel.kt`
- Modify: `android/app/src/main/res/values/strings_catalog.xml`
- Create: `android/app/src/test/java/com/mykiot/pos/feature/product/AddProductViewModelTest.kt`

**Interfaces:**
- Consumes: `ProductRepository.get/create/update` (Task 3), `CategoryRepository.tree(): ApiResult<List<CategoryNodeDto>>` (đã có ở `feature/category/data/CategoryRepository.kt`), `SessionManager.isOwner: Boolean` (đã có ở `core/auth/SessionManager.kt`).
- Produces: `AddProductUiState` với field mới (`minStock`, `status`, `categoryId`, `categoryLabel`, `categories: List<CategoryOption>`, `isOwner`, `editingId`, `saved`); hàm `startEdit(id)`, `loadCategories()`, `onMinStock`, `onStatus`, `onCategory`. Dùng ở Task 5 (`AddProductScreen`).

- [ ] **Step 1: Thêm string resource mới**

Trong `android/app/src/main/res/values/strings_catalog.xml`, thêm vào cuối khối `<!-- ViewModel (AddProductViewModel) -->` (sau dòng 42):

```xml
    <string name="cat_product_edit">Sửa sản phẩm</string>
    <string name="cat_product_field_category">Nhóm hàng</string>
    <string name="cat_product_field_category_none">Không có nhóm</string>
    <string name="cat_product_field_min_stock">Tồn tối thiểu</string>
    <string name="cat_product_field_status">Trạng thái</string>
    <string name="cat_product_status_draft">Nháp</string>
    <string name="cat_product_err_unit_required">Vui lòng nhập đơn vị tính</string>
    <string name="cat_product_err_sale_price_required">Vui lòng nhập giá bán</string>
    <string name="cat_product_err_cost_price_required">Vui lòng nhập giá vốn</string>
    <string name="cat_product_delete">Xóa sản phẩm</string>
    <string name="cat_product_delete_confirm_title">Xóa sản phẩm?</string>
    <string name="cat_product_delete_confirm_message">Sản phẩm sẽ bị ẩn khỏi toàn bộ hệ thống và không thể khôi phục.</string>
```

- [ ] **Step 2: Viết test thất bại cho `AddProductViewModelTest.kt`**

Tạo `android/app/src/test/java/com/mykiot/pos/feature/product/AddProductViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.product

import com.mykiot.pos.R
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.feature.category.data.CategoryRepository
import com.mykiot.pos.feature.product.data.ProductRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
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

class AddProductViewModelTest {
    private val repo = mockk<ProductRepository>(relaxed = true)
    private val categoryRepo = mockk<CategoryRepository>(relaxed = true)
    private val session = mockk<SessionManager>(relaxed = true)
    private val res = FakeResProvider()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun vm(isOwner: Boolean = true): AddProductViewModel {
        every { session.isOwner } returns isOwner
        return AddProductViewModel(repo, categoryRepo, session, res)
    }

    @Test
    fun `blank name sets error, no api call`() = runTest {
        val viewModel = vm()
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(R.string.cat_product_err_name_required), viewModel.state.value.error?.message)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `blank unit sets error, no api call`() = runTest {
        val viewModel = vm()
        viewModel.onName("Coca")
        viewModel.onUnit("")
        viewModel.onSale("12000")
        viewModel.onCost("9000")
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(R.string.cat_product_err_unit_required), viewModel.state.value.error?.message)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `blank sale price sets error, no api call`() = runTest {
        val viewModel = vm()
        viewModel.onName("Coca")
        viewModel.onCost("9000")
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(R.string.cat_product_err_sale_price_required), viewModel.state.value.error?.message)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `owner with blank cost price sets error, no api call`() = runTest {
        val viewModel = vm(isOwner = true)
        viewModel.onName("Coca")
        viewModel.onSale("12000")
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(R.string.cat_product_err_cost_price_required), viewModel.state.value.error?.message)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test
    fun `cashier with blank cost price still saves with default zero`() = runTest {
        coEvery { repo.create(any()) } returns ApiResult.Success(
            ProductBriefDto(id = 1, sku = "SP000001", name = "Coca", unit = "lon", salePrice = 12000.0, status = "ACTIVE"),
        )
        val viewModel = vm(isOwner = false)
        viewModel.onName("Coca")
        viewModel.onUnit("lon")
        viewModel.onSale("12000")
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.create(ProductCreateDto(name = "Coca", unit = "lon", costPrice = "0", salePrice = "12000")) }
        assertTrue(viewModel.state.value.saved)
    }

    @Test
    fun `create path calls repo create with trimmed fields`() = runTest {
        coEvery { repo.create(any()) } returns ApiResult.Success(
            ProductBriefDto(id = 1, sku = "SP000001", name = "Coca", unit = "lon", salePrice = 12000.0, status = "ACTIVE"),
        )
        val viewModel = vm(isOwner = true)
        viewModel.onName(" Coca ")
        viewModel.onUnit("lon")
        viewModel.onCost("9000")
        viewModel.onSale("12000")
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.create(ProductCreateDto(name = "Coca", unit = "lon", costPrice = "9000", salePrice = "12000")) }
        assertTrue(viewModel.state.value.saved)
    }

    @Test
    fun `startEdit loads product then submit calls update`() = runTest {
        coEvery { repo.get(9) } returns ApiResult.Success(
            ProductBriefDto(
                id = 9, sku = "SP000009", name = "Pepsi", unit = "chai",
                salePrice = 15000.0, costPrice = 11000.0, status = "ACTIVE",
            ),
        )
        coEvery { repo.update(eq(9), any()) } returns ApiResult.Success(
            ProductBriefDto(id = 9, sku = "SP000009", name = "Pepsi 1.5L", unit = "chai", salePrice = 15000.0, status = "ACTIVE"),
        )
        val viewModel = vm(isOwner = true)
        viewModel.startEdit(9)
        testScheduler.advanceUntilIdle()
        assertEquals("Pepsi", viewModel.state.value.name)
        assertEquals("11000", viewModel.state.value.costPrice)
        viewModel.onName("Pepsi 1.5L")
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.update(eq(9), any()) }
        assertTrue(viewModel.state.value.saved)
    }

    @Test
    fun `cashier editing product sends null cost price to avoid overwriting hidden value`() = runTest {
        // Cashier GET response has costPrice = null (ẩn theo can_see_cost ở backend) — nếu submit()
        // gửi "0" thay vì null, sẽ ghi đè giá vốn thật của OWNER về 0 (mất dữ liệu).
        coEvery { repo.get(9) } returns ApiResult.Success(
            ProductBriefDto(
                id = 9, sku = "SP000009", name = "Pepsi", unit = "chai",
                salePrice = 15000.0, costPrice = null, status = "ACTIVE",
            ),
        )
        coEvery { repo.update(eq(9), any()) } returns ApiResult.Success(
            ProductBriefDto(id = 9, sku = "SP000009", name = "Pepsi", unit = "chai", salePrice = 15000.0, status = "ACTIVE"),
        )
        val viewModel = vm(isOwner = false)
        viewModel.startEdit(9)
        testScheduler.advanceUntilIdle()
        viewModel.submit()
        testScheduler.advanceUntilIdle()
        coVerify { repo.update(eq(9), match { it.costPrice == null }) }
        assertTrue(viewModel.state.value.saved)
    }

    @Test
    fun `loadCategories flattens tree with indentation for children`() = runTest {
        coEvery { categoryRepo.tree() } returns ApiResult.Success(
            listOf(
                CategoryNodeDto(id = 1, name = "Đồ uống", children = listOf(CategoryNodeDto(id = 2, name = "Nước ngọt"))),
            ),
        )
        val viewModel = vm()
        viewModel.loadCategories()
        testScheduler.advanceUntilIdle()
        assertEquals(listOf("Đồ uống", "— Nước ngọt"), viewModel.state.value.categories.map { it.label })
    }
}
```

- [ ] **Step 3: Chạy test, xác nhận FAIL (biên dịch lỗi vì constructor/hàm chưa tồn tại)**

Run: `cd android && ./gradlew testDebugUnitTest --tests "com.mykiot.pos.feature.product.AddProductViewModelTest"`
Expected: FAIL biên dịch — `AddProductViewModel` hiện chỉ nhận `(repository, res)`, chưa có `categoryRepository`/`sessionManager`, chưa có `startEdit`/`onMinStock`/`onStatus`/`loadCategories`.

- [ ] **Step 4: Viết implementation — thay toàn bộ `AddProductViewModel.kt`**

```kotlin
package com.mykiot.pos.feature.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.R
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.core.network.dto.ProductUpdateDto
import com.mykiot.pos.feature.category.data.CategoryRepository
import com.mykiot.pos.feature.product.data.ProductRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import javax.inject.Inject

data class CategoryOption(val id: Long, val label: String)

data class AddProductUiState(
    val name: String = "",
    val barcode: String = "",
    val sku: String = "",
    val unit: String = "cái",
    val costPrice: String = "",
    val salePrice: String = "",
    val minStock: String = "0",
    val status: String = "ACTIVE",
    val categoryId: Long? = null,
    val categoryLabel: String = "",
    val categories: List<CategoryOption> = emptyList(),
    val isOwner: Boolean = false,
    val editingId: Long? = null,
    val loading: Boolean = false,
    val error: ApiError? = null,
    val created: ProductBriefDto? = null,
    val saved: Boolean = false,
)

@HiltViewModel
class AddProductViewModel @Inject constructor(
    private val repository: ProductRepository,
    private val categoryRepository: CategoryRepository,
    private val sessionManager: SessionManager,
    private val res: ResProvider,
) : ViewModel() {

    private val _state = MutableStateFlow(AddProductUiState(isOwner = sessionManager.isOwner))
    val state: StateFlow<AddProductUiState> = _state.asStateFlow()

    private var prefilled = false
    private var categoriesLoaded = false

    fun prefillBarcode(barcode: String) {
        if (prefilled) return
        prefilled = true
        if (barcode.isNotBlank()) _state.update { it.copy(barcode = barcode) }
    }

    fun loadCategories() {
        if (categoriesLoaded) return
        categoriesLoaded = true
        viewModelScope.launch {
            when (val r = categoryRepository.tree()) {
                is ApiResult.Success -> {
                    // `startEdit` và `loadCategories` chạy song song (2 LaunchedEffect độc lập ở
                    // Composable) — nếu categoryId đã có trước khi list nhóm hàng về, backfill lại
                    // label ở đây để không bị kẹt ở "Không có nhóm" khi thực ra đã có category_id.
                    val options = flattenCategories(r.data)
                    _state.update { current ->
                        current.copy(
                            categories = options,
                            categoryLabel = options.find { it.id == current.categoryId }?.label ?: current.categoryLabel,
                        )
                    }
                }
                is ApiResult.Failure -> Unit // Không chặn form nếu tải nhóm hàng lỗi
            }
        }
    }

    fun startEdit(id: Long) {
        if (_state.value.editingId == id) return
        _state.update { it.copy(editingId = id, loading = true) }
        viewModelScope.launch {
            when (val r = repository.get(id)) {
                is ApiResult.Success -> {
                    val p = r.data
                    _state.update { current ->
                        current.copy(
                            loading = false,
                            name = p.name,
                            barcode = p.barcode ?: "",
                            sku = p.sku,
                            unit = p.unit,
                            costPrice = p.costPrice?.toLong()?.toString() ?: "",
                            salePrice = p.salePrice.toLong().toString(),
                            minStock = p.minStock.toString(),
                            status = p.status,
                            categoryId = p.categoryId,
                            categoryLabel = current.categories.find { it.id == p.categoryId }?.label ?: "",
                        )
                    }
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun onName(v: String) = _state.update { it.copy(name = v) }
    fun onBarcode(v: String) = _state.update { it.copy(barcode = v) }
    fun onSku(v: String) = _state.update { it.copy(sku = v) }
    fun onUnit(v: String) = _state.update { it.copy(unit = v) }
    fun onCost(v: String) = _state.update { it.copy(costPrice = v) }
    fun onSale(v: String) = _state.update { it.copy(salePrice = v) }
    fun onMinStock(v: String) = _state.update { it.copy(minStock = v) }
    fun onStatus(v: String) = _state.update { it.copy(status = v) }
    fun onCategory(id: Long?, label: String) = _state.update { it.copy(categoryId = id, categoryLabel = label) }
    fun clearError() = _state.update { it.copy(error = null) }

    private fun normalizePrice(v: String): String? {
        val t = v.trim().replace(",", "")
        if (t.isBlank()) return "0"
        return try { BigDecimal(t); t } catch (_: Exception) { null }
    }

    fun submit() {
        val s = _state.value
        if (s.name.isBlank()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_name_required))) }
            return
        }
        if (s.unit.isBlank()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_unit_required))) }
            return
        }
        val cost = normalizePrice(s.costPrice)
        val sale = normalizePrice(s.salePrice)
        if (cost == null || sale == null) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_price_invalid))) }
            return
        }
        if (sale == "0") {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_sale_price_required))) }
            return
        }
        if (s.isOwner && cost == "0") {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_cost_price_required))) }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            val editId = s.editingId
            val trimmedName = s.name.trim()
            val trimmedSku = s.sku.trim().ifBlank { null }
            val trimmedBarcode = s.barcode.trim().ifBlank { null }
            val trimmedUnit = s.unit.trim().ifBlank { "cái" }
            val minStock = s.minStock.toIntOrNull() ?: 0
            val result = if (editId != null) {
                repository.update(
                    editId,
                    ProductUpdateDto(
                        name = trimmedName,
                        sku = trimmedSku,
                        barcode = trimmedBarcode,
                        categoryId = s.categoryId,
                        unit = trimmedUnit,
                        costPrice = if (s.isOwner) cost else null,
                        salePrice = sale,
                        minStock = minStock,
                        status = s.status,
                    ),
                )
            } else {
                repository.create(
                    ProductCreateDto(
                        name = trimmedName,
                        sku = trimmedSku,
                        barcode = trimmedBarcode,
                        categoryId = s.categoryId,
                        unit = trimmedUnit,
                        costPrice = cost,
                        salePrice = sale,
                        minStock = minStock,
                        status = s.status,
                    ),
                )
            }
            when (result) {
                is ApiResult.Success -> {
                    val createdDto = if (editId == null) result.data else null
                    _state.update { it.copy(loading = false, saved = true, created = createdDto) }
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = result.error) }
            }
        }
    }
}

private fun flattenCategories(nodes: List<CategoryNodeDto>, depth: Int = 0): List<CategoryOption> {
    val out = mutableListOf<CategoryOption>()
    for (n in nodes) {
        out += CategoryOption(n.id, "— ".repeat(depth) + n.name)
        if (n.children.isNotEmpty()) out += flattenCategories(n.children, depth + 1)
    }
    return out
}
```

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd android && ./gradlew testDebugUnitTest --tests "com.mykiot.pos.feature.product.AddProductViewModelTest"`
Expected: BUILD SUCCESSFUL, 9 test PASS.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/product/AddProductViewModel.kt \
        android/app/src/main/res/values/strings_catalog.xml \
        android/app/src/test/java/com/mykiot/pos/feature/product/AddProductViewModelTest.kt
git commit -m "feat(android): AddProductViewModel hỗ trợ sửa SP + validate bắt buộc đơn vị/giá"
```

---

### Task 5: Android — UI `AddProductScreen` (nhóm hàng, tồn tối thiểu, trạng thái) + route Sửa SP

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/AddProductScreen.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/Routes.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt:145-147`

**Interfaces:**
- Consumes: `AddProductViewModel` state/hàm mới từ Task 4.
- Produces: `AddProductScreen(initialBarcode, productId: Long? = null, onCreated, onSaved: () -> Unit = {}, onCancel, viewModel)`; `Routes.PRODUCT_EDIT` + `Routes.productEdit(id)`. Dùng ở Task 6 (nút "Sửa" trên `ProductDetailScreen`).

- [ ] **Step 1: Thay toàn bộ `AddProductScreen.kt`**

```kotlin
package com.mykiot.pos.feature.product

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.hardware.scanner.MlKitScannerScreen
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MoneyInput
import com.mykiot.pos.feature.supplier.FormTopBar

/**
 * Màn thêm / sửa sản phẩm.
 *
 * Hai chế độ:
 * - Thêm mới (productId == null): mở từ danh sách SP hoặc từ luồng quét mã lạ ở tab Nhập
 *   (prefill barcode). Tạo xong → trả [ProductBriefDto] qua [onCreated] để thêm thẳng vào phiếu nhập.
 * - Sửa (productId != null): nạp dữ liệu hiện tại qua [AddProductViewModel.startEdit], lưu xong → [onSaved].
 */
@Composable
fun AddProductScreen(
    initialBarcode: String = "",
    productId: Long? = null,
    onCreated: (ProductBriefDto) -> Unit = {},
    onSaved: () -> Unit = {},
    onCancel: () -> Unit,
    viewModel: AddProductViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showScanner by remember { mutableStateOf(false) }
    var showCategoryMenu by remember { mutableStateOf(false) }
    var showStatusMenu by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.loadCategories() }
    LaunchedEffect(productId) {
        if (productId != null) viewModel.startEdit(productId) else viewModel.prefillBarcode(initialBarcode)
    }
    LaunchedEffect(state.created) {
        state.created?.let(onCreated)
    }
    LaunchedEffect(state.saved) {
        if (state.saved) onSaved()
    }

    if (showScanner) {
        MlKitScannerScreen(
            onScanned = { code -> showScanner = false; viewModel.onBarcode(code) },
            onClose = { showScanner = false },
        )
        return
    }

    val statusOptions = listOf(
        "ACTIVE" to stringResource(R.string.cat_product_status_active),
        "INACTIVE" to stringResource(R.string.cat_product_status_inactive),
        "DRAFT" to stringResource(R.string.cat_product_status_draft),
    )
    val title = stringResource(if (state.editingId != null) R.string.cat_product_edit else R.string.cat_product_add)

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            FormTopBar(title = title, onBack = onCancel)

            AppTextField(
                value = state.name,
                onValueChange = viewModel::onName,
                label = stringResource(R.string.cat_product_field_name),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            AppTextField(
                value = state.barcode,
                onValueChange = viewModel::onBarcode,
                label = stringResource(R.string.cat_product_field_barcode),
                modifier = Modifier.fillMaxWidth(),
                trailingIcon = {
                    IconButton(onClick = { showScanner = true }) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = stringResource(R.string.cat_product_scan_barcode))
                    }
                },
            )
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                AppTextField(
                    value = state.sku,
                    onValueChange = viewModel::onSku,
                    label = stringResource(R.string.cat_product_field_sku),
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                AppTextField(
                    value = state.unit,
                    onValueChange = viewModel::onUnit,
                    label = stringResource(R.string.cat_product_field_unit),
                    modifier = Modifier.width(120.dp),
                )
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                MoneyInput(
                    value = state.costPrice.toLongOrNull() ?: 0L,
                    onValueChange = { viewModel.onCost(it.toString()) },
                    label = stringResource(R.string.cat_product_field_cost),
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                MoneyInput(
                    value = state.salePrice.toLongOrNull() ?: 0L,
                    onValueChange = { viewModel.onSale(it.toString()) },
                    label = stringResource(R.string.cat_product_field_sale),
                    modifier = Modifier.weight(1f),
                )
            }
            Spacer(Modifier.height(12.dp))
            Box {
                DropdownField(
                    label = stringResource(R.string.cat_product_field_category),
                    selectedText = state.categoryLabel.ifBlank { stringResource(R.string.cat_product_field_category_none) },
                    onClick = { showCategoryMenu = true },
                    modifier = Modifier.fillMaxWidth(),
                )
                DropdownMenu(expanded = showCategoryMenu, onDismissRequest = { showCategoryMenu = false }) {
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.cat_product_field_category_none)) },
                        onClick = { viewModel.onCategory(null, ""); showCategoryMenu = false },
                    )
                    state.categories.forEach { c ->
                        DropdownMenuItem(
                            text = { Text(c.label) },
                            onClick = { viewModel.onCategory(c.id, c.label); showCategoryMenu = false },
                        )
                    }
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                AppTextField(
                    value = state.minStock,
                    onValueChange = viewModel::onMinStock,
                    label = stringResource(R.string.cat_product_field_min_stock),
                    keyboardType = KeyboardType.Number,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                Box(Modifier.weight(1f)) {
                    DropdownField(
                        label = stringResource(R.string.cat_product_field_status),
                        selectedText = statusOptions.first { it.first == state.status }.second,
                        onClick = { showStatusMenu = true },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    DropdownMenu(expanded = showStatusMenu, onDismissRequest = { showStatusMenu = false }) {
                        statusOptions.forEach { (value, label) ->
                            DropdownMenuItem(
                                text = { Text(label) },
                                onClick = { viewModel.onStatus(value); showStatusMenu = false },
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(24.dp))
            Button(
                onClick = viewModel::submit,
                enabled = !state.loading,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.onSurface,
                    contentColor = MaterialTheme.colorScheme.surface,
                ),
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) { Text(stringResource(R.string.cat_product_save), fontWeight = FontWeight.SemiBold) }
            Spacer(Modifier.height(24.dp))
        }
    }

    LoadingDialog(visible = state.loading, message = stringResource(R.string.cat_product_saving))
    state.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

/** Ô dạng field chỉ đọc, bấm để mở [DropdownMenu] neo ngay bên dưới (nhóm hàng / trạng thái). */
@Composable
private fun DropdownField(
    label: String,
    selectedText: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(4.dp))
        Row(
            Modifier
                .fillMaxWidth()
                .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(14.dp))
                .clickable(onClick = onClick)
                .padding(horizontal = 16.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(selectedText, modifier = Modifier.weight(1f))
            Icon(Icons.Filled.ArrowDropDown, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
```

- [ ] **Step 2: Thêm route Sửa SP trong `Routes.kt`**

Trong `android/app/src/main/java/com/mykiot/pos/navigation/Routes.kt`, sửa dòng 20 và 33-37:

```kotlin
    const val PRODUCT_ADD = "product_add"
    const val PRODUCT_EDIT = "product_edit/{id}"
```

```kotlin
    fun receiptDetail(id: Long) = "receipt_detail/$id"
    fun customerDetail(id: Long) = "customer_detail/$id"
    fun productDetail(id: Long) = "product_detail/$id"
    fun productEdit(id: Long) = "product_edit/$id"
    fun invoiceDetail(id: Long) = "invoice_detail/$id"
    fun returnNew(invoiceId: Long) = "return_new/$invoiceId"
    fun supplierEdit(id: Long) = "supplier_edit/$id"
```

- [ ] **Step 3: Wire route trong `HomeNavHost.kt`**

Trong `android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt`, thay dòng 145-147:

```kotlin
        composable(Routes.PRODUCT_ADD) { entry ->
            AddProductScreen(onCreated = { nav.popOnce(entry) }, onCancel = { nav.popOnce(entry) })
        }
        composable(
            Routes.PRODUCT_EDIT,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            AddProductScreen(productId = id, onSaved = { nav.popOnce(entry) }, onCancel = { nav.popOnce(entry) })
        }
```

- [ ] **Step 4: Biên dịch để xác nhận không lỗi**

Run: `cd android && ./gradlew compileDebugKotlin`
Expected: BUILD SUCCESSFUL. Lưu ý: `ProductDetailScreen` gọi trong `HomeNavHost.kt:143` chưa có tham số `onEdit` — sẽ thêm ở Task 6, KHÔNG sửa dòng đó ở task này để tránh biên dịch lỗi tạm thời giữa 2 task (composable `ProductDetailScreen` giữ nguyên chữ ký hiện có cho tới Task 6).

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/product/AddProductScreen.kt \
        android/app/src/main/java/com/mykiot/pos/navigation/Routes.kt \
        android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt
git commit -m "feat(android): thêm nhóm hàng/tồn tối thiểu/trạng thái vào form SP + route Sửa SP"
```

---

### Task 6: Android — Xóa sản phẩm (OWNER-only) + nút Sửa trên màn Chi tiết

**Files:**
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/ProductDetailViewModel.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/feature/product/ProductDetailScreen.kt`
- Modify: `android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt:138-144`
- Modify: `android/app/src/test/java/com/mykiot/pos/feature/product/ProductDetailViewModelTest.kt`

**Interfaces:**
- Consumes: `ProductListRepository.delete(id)` (Task 3), `SessionManager.isOwner` (đã có), `Routes.productEdit(id)` (Task 5), `ConfirmDialog`/`ErrorDialog` (đã có ở `core/ui`).
- Produces: `ProductDetailScreen(productId, onBack, onEdit: (Long) -> Unit, viewModel)`.

- [ ] **Step 1: Viết test thất bại cho delete trong `ProductDetailViewModelTest.kt`**

Thay toàn bộ nội dung `android/app/src/test/java/com/mykiot/pos/feature/product/ProductDetailViewModelTest.kt`:

```kotlin
package com.mykiot.pos.feature.product

import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.product.data.ProductListRepository
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ProductDetailViewModelTest {
    private val repo = mockk<ProductListRepository>()
    private val session = mockk<SessionManager>()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun vm(isOwner: Boolean = true): ProductDetailViewModel {
        every { session.isOwner } returns isOwner
        return ProductDetailViewModel(repo, session)
    }

    @Test
    fun `load fetches product by id`() = runTest {
        coEvery { repo.get(3) } returns ApiResult.Success(
            ProductBriefDto(id = 3, sku = "SP000003", name = "Coca", unit = "lon", salePrice = 12000.0, status = "ACTIVE"),
        )
        val viewModel = vm()
        viewModel.load(3)
        testScheduler.advanceUntilIdle()
        assertEquals("Coca", viewModel.state.value.product?.name)
    }

    @Test
    fun `isOwner reflects session at construction`() {
        assertTrue(vm(isOwner = true).state.value.isOwner)
        assertFalse(vm(isOwner = false).state.value.isOwner)
    }

    @Test
    fun `delete success sets deleted flag`() = runTest {
        coEvery { repo.delete(5) } returns ApiResult.Success(Unit)
        val viewModel = vm()
        viewModel.delete(5)
        testScheduler.advanceUntilIdle()
        assertTrue(viewModel.state.value.deleted)
        assertNull(viewModel.state.value.deleteError)
    }

    @Test
    fun `delete failure sets deleteError, not deleted`() = runTest {
        coEvery { repo.delete(5) } returns ApiResult.Failure(ApiError("FORBIDDEN", "Bạn không có quyền thực hiện"))
        val viewModel = vm()
        viewModel.delete(5)
        testScheduler.advanceUntilIdle()
        assertEquals("Bạn không có quyền thực hiện", viewModel.state.value.deleteError?.message)
        assertFalse(viewModel.state.value.deleted)
    }
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd android && ./gradlew testDebugUnitTest --tests "com.mykiot.pos.feature.product.ProductDetailViewModelTest"`
Expected: FAIL biên dịch — `ProductDetailViewModel` hiện chỉ nhận `(repository)`, chưa có `sessionManager`, chưa có `delete`/`isOwner`/`deleted`/`deleteError`.

- [ ] **Step 3: Thay toàn bộ `ProductDetailViewModel.kt`**

```kotlin
package com.mykiot.pos.feature.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.product.data.ProductListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProductDetailUiState(
    val product: ProductBriefDto? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val deleteError: ApiError? = null,
    val isOwner: Boolean = false,
    val deleted: Boolean = false,
)

@HiltViewModel
class ProductDetailViewModel @Inject constructor(
    private val repository: ProductListRepository,
    sessionManager: SessionManager,
) : ViewModel() {
    private val _state = MutableStateFlow(ProductDetailUiState(isOwner = sessionManager.isOwner))
    val state: StateFlow<ProductDetailUiState> = _state.asStateFlow()

    fun load(id: Long) {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.get(id)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, product = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun delete(id: Long) {
        _state.update { it.copy(loading = true, deleteError = null) }
        viewModelScope.launch {
            when (val r = repository.delete(id)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, deleted = true) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, deleteError = r.error) }
            }
        }
    }

    fun clearDeleteError() = _state.update { it.copy(deleteError = null) }
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd android && ./gradlew testDebugUnitTest --tests "com.mykiot.pos.feature.product.ProductDetailViewModelTest"`
Expected: BUILD SUCCESSFUL, 4 test PASS.

- [ ] **Step 5: Thay toàn bộ `ProductDetailScreen.kt`**

```kotlin
package com.mykiot.pos.feature.product

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.ConfirmDialog
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.SectionHeader
import com.mykiot.pos.core.ui.Spacing
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ProductDetailScreen(
    productId: Long,
    onBack: () -> Unit,
    onEdit: (Long) -> Unit,
    viewModel: ProductDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showDeleteConfirm by remember { mutableStateOf(false) }
    LaunchedEffect(productId) { viewModel.load(productId) }
    LaunchedEffect(state.deleted) { if (state.deleted) onBack() }
    val p = state.product

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = p?.name ?: stringResource(R.string.cat_product_title),
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
                actions = {
                    IconButton(onClick = { onEdit(productId) }, enabled = !state.loading) {
                        Icon(Icons.Filled.Edit, contentDescription = stringResource(R.string.cat_product_edit))
                    }
                    if (state.isOwner) {
                        IconButton(onClick = { showDeleteConfirm = true }, enabled = !state.loading) {
                            Icon(Icons.Filled.Delete, contentDescription = stringResource(R.string.cat_product_delete))
                        }
                    }
                },
            )
        },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.lg, vertical = Spacing.md),
        ) {
            if (p == null) {
                Text(
                    state.errorMessage ?: stringResource(R.string.cat_product_loading_short),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                InfoRow(stringResource(R.string.cat_product_label_sku), p.sku)
                p.barcode?.let { InfoRow(stringResource(R.string.cat_product_label_barcode), it) }
                InfoRow(stringResource(R.string.cat_product_label_unit), p.unit)
                InfoRow(stringResource(R.string.cat_product_label_sale_price), formatVnd(p.salePrice.toLong()))
                p.costPrice?.let { InfoRow(stringResource(R.string.cat_product_label_cost_price), formatVnd(it.toLong())) }
                InfoRow(
                    stringResource(R.string.cat_product_label_status),
                    if (p.status == "ACTIVE") stringResource(R.string.cat_product_status_active) else stringResource(R.string.cat_product_status_inactive),
                )
                InfoRow(
                    stringResource(R.string.cat_product_label_allow_negative),
                    if (p.allowNegative) stringResource(R.string.cat_product_yes) else stringResource(R.string.cat_product_no),
                )
                if (p.units.isNotEmpty()) {
                    Spacer(Modifier.height(Spacing.lg))
                    SectionHeader(stringResource(R.string.cat_product_units_section))
                    Spacer(Modifier.height(Spacing.sm))
                    p.units.forEach { u ->
                        InfoRow(u.unitName, stringResource(R.string.cat_product_unit_conversion, u.conversionRate))
                    }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading && state.product == null, message = stringResource(R.string.cat_product_loading))

    if (showDeleteConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.cat_product_delete_confirm_title),
            message = stringResource(R.string.cat_product_delete_confirm_message),
            onConfirm = { viewModel.delete(productId) },
            onDismiss = { showDeleteConfirm = false },
        )
    }
    state.deleteError?.let { ErrorDialog(it) { viewModel.clearDeleteError() } }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.Medium)
    }
}
```

- [ ] **Step 6: Wire `onEdit` trong `HomeNavHost.kt`**

Trong `android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt`, thay dòng 138-144:

```kotlin
        composable(
            Routes.PRODUCT_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            ProductDetailScreen(
                productId = id,
                onBack = { nav.popOnce(entry) },
                onEdit = { nav.navigateOnce(entry, Routes.productEdit(it)) },
            )
        }
```

- [ ] **Step 7: Biên dịch toàn bộ module + chạy lại toàn bộ unit test product**

Run: `cd android && ./gradlew compileDebugKotlin testDebugUnitTest --tests "com.mykiot.pos.feature.product.*"`
Expected: BUILD SUCCESSFUL, tất cả test trong `feature/product` PASS (bao gồm `ProductListViewModelTest` không đổi, `AddProductViewModelTest` từ Task 4, `ProductDetailViewModelTest` cập nhật).

- [ ] **Step 8: Commit**

```bash
git add android/app/src/main/java/com/mykiot/pos/feature/product/ProductDetailViewModel.kt \
        android/app/src/main/java/com/mykiot/pos/feature/product/ProductDetailScreen.kt \
        android/app/src/main/java/com/mykiot/pos/navigation/HomeNavHost.kt \
        android/app/src/test/java/com/mykiot/pos/feature/product/ProductDetailViewModelTest.kt
git commit -m "feat(android): thêm xóa sản phẩm (OWNER-only) + nút Sửa trên màn chi tiết"
```

---

### Task 7: Kiểm tra tích hợp cuối cùng

**Files:** không tạo/sửa file mới — chỉ chạy full test suite của 3 stack để xác nhận không có regression giữa các task.

- [ ] **Step 1: Chạy toàn bộ test backend**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS toàn bộ (bao gồm `test_product.py`, `test_product_units.py` không đổi hành vi).

- [ ] **Step 2: Build web**

Run: `cd frontend && npm run build`
Expected: build thành công.

- [ ] **Step 3: Chạy toàn bộ unit test Android**

Run: `cd android && ./gradlew testDebugUnitTest`
Expected: BUILD SUCCESSFUL, không có test nào ở các feature khác (`supplier`, `receipt`, `pos`, `category`) bị phá bởi field mới trong `ProductBriefDto`/`ProductCreateDto`.

- [ ] **Step 4: Build Android debug APK (xác nhận biên dịch toàn bộ, kể cả Compose)**

Run: `cd android && ./gradlew assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Smoke test thủ công (ghi chú cho người review, không tự động hoá)**

Cài APK debug lên thiết bị/emulator, đăng nhập OWNER:
1. Sản phẩm → Thêm SP → để trống đơn vị/giá vốn/giá bán → xác nhận báo lỗi tiếng Việt đúng field.
2. Điền đủ + chọn nhóm hàng + trạng thái "Nháp" → Lưu → mở lại Chi tiết SP → xác nhận đúng dữ liệu.
3. Bấm "Sửa" ở Chi tiết SP → đổi tồn tối thiểu → Lưu → xác nhận cập nhật.
4. Bấm "Xóa" → xác nhận dialog cảnh báo → xác nhận SP biến mất khỏi danh sách.
5. Đăng nhập lại bằng tài khoản CASHIER (tạo qua Cài đặt nhân viên) → mở Chi tiết 1 SP → xác nhận KHÔNG thấy nút Xóa, form Thêm SP không bắt buộc giá vốn.

Đây là bước không tự động hoá được (không có Compose UI test / instrumented test trong repo) — ghi lại kết quả smoke test trước khi coi task hoàn tất.
