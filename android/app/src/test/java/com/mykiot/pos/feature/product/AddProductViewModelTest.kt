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
