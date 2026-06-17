package com.mykiot.pos.feature.product

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
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

    private fun page(vararg items: ProductBriefDto, page: Int = 1, totalPages: Int = 1) =
        ApiResult.Success(PageResult(items.toList(), page, totalPages))

    @Test fun `load populates items on success`() = runTest {
        coEvery { repo.list(null, any()) } returns page(product(1), product(2))
        val vm = ProductListViewModel(repo)
        assertEquals(2, vm.paging.value.items.size)
        assertEquals("Sản phẩm 1", vm.paging.value.items.first().name)
        assertFalse(vm.paging.value.refreshing)
    }

    @Test fun `load sets errorMessage on failure`() = runTest {
        coEvery { repo.list(null, any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi mạng"))
        val vm = ProductListViewModel(repo)
        assertEquals("Lỗi mạng", vm.paging.value.errorMessage)
        assertFalse(vm.paging.value.refreshing)
    }

    @Test fun `onQueryChange with 2 chars calls repo with query`() = runTest {
        coEvery { repo.list(any(), any()) } returns page()
        val vm = ProductListViewModel(repo)
        vm.onQueryChange("SP")
        coVerify { repo.list("SP", 1) }
    }

    @Test fun `onQueryChange blank calls repo with null`() = runTest {
        coEvery { repo.list(any(), any()) } returns page()
        val vm = ProductListViewModel(repo)
        vm.onQueryChange("")
        coVerify { repo.list(null, 1) }
    }

    @Test fun `loadMore appends next page items`() = runTest {
        coEvery { repo.list(null, 1) } returns page(product(1), totalPages = 2)
        coEvery { repo.list(null, 2) } returns page(product(2), page = 2, totalPages = 2)
        val vm = ProductListViewModel(repo)
        vm.loadMore()
        assertEquals(2, vm.paging.value.items.size)
        assertEquals(2, vm.paging.value.page)
        assertFalse(vm.paging.value.canLoadMore)
    }

    @Test fun `loadMore does nothing when no more pages`() = runTest {
        coEvery { repo.list(null, 1) } returns page(product(1), totalPages = 1)
        val vm = ProductListViewModel(repo)
        vm.loadMore()
        coVerify(exactly = 0) { repo.list(null, 2) }
    }

    @Test fun `clearError removes errorMessage`() = runTest {
        coEvery { repo.list(null, any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi"))
        val vm = ProductListViewModel(repo)
        vm.clearError()
        assertNull(vm.paging.value.errorMessage)
    }
}
