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
