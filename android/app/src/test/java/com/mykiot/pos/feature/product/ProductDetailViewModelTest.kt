package com.mykiot.pos.feature.product

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.product.data.ProductListRepository
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

class ProductDetailViewModelTest {
    private val repo = mockk<ProductListRepository>()
    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `load fetches product by id`() = runTest {
        coEvery { repo.get(3) } returns ApiResult.Success(
            ProductBriefDto(id = 3, sku = "SP000003", name = "Coca", unit = "lon", salePrice = 12000.0, status = "ACTIVE"),
        )
        val vm = ProductDetailViewModel(repo)
        vm.load(3)
        testScheduler.advanceUntilIdle()
        assertEquals("Coca", vm.state.value.product?.name)
    }
}
