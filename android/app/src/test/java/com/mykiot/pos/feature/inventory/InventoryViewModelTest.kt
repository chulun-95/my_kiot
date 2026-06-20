package com.mykiot.pos.feature.inventory

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.feature.inventory.data.InventoryRepository
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
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class InventoryViewModelTest {

    private val repo: InventoryRepository = mockk(relaxed = true)
    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun item(id: Long) = InventoryItemDto(
        productId = id, productSku = "SKU$id", productName = "SP$id",
        unit = "cái", quantity = "12", minStock = 5, salePrice = "10000",
    )

    private fun page(vararg items: InventoryItemDto, page: Int = 1, totalPages: Int = 1) =
        ApiResult.Success(PageResult(items.toList(), page, totalPages))

    @Test fun `load populates items`() = runTest {
        coEvery { repo.list(any(), any()) } returns page(item(1), item(2))
        val vm = InventoryViewModel(repo)

        vm.load()

        assertEquals(2, vm.paging.value.items.size)
        assertEquals(false, vm.paging.value.refreshing)
    }

    @Test fun `load failure shows vietnamese error`() = runTest {
        coEvery { repo.list(any(), any()) } returns ApiResult.Failure(ApiError("SERVER", "Lỗi máy chủ", 500))
        val vm = InventoryViewModel(repo)

        vm.load()

        assertEquals("Lỗi máy chủ", vm.paging.value.error?.message)
    }

    @Test fun `openMovements loads kardex`() = runTest {
        coEvery { repo.movements(1) } returns ApiResult.Success(emptyList())
        val vm = InventoryViewModel(repo)

        vm.openMovements(item(1))

        assertEquals(1L, vm.movements.value.item?.productId)
    }

    @Test fun `selectTab LOW loads low stock items`() = runTest {
        coEvery { repo.list(any(), any()) } returns page()
        coEvery { repo.lowStock() } returns ApiResult.Success(
            listOf(InventoryItemDto(productId = 1, productSku = "SP1", productName = "Mì gói", unit = "gói", quantity = "2", minStock = 5, salePrice = "5000"))
        )
        val vm = InventoryViewModel(repo)

        vm.selectTab(InventoryTab.LOW)

        assertEquals(InventoryTab.LOW, vm.tab.value)
        assertEquals(1, vm.lowStock.value.items.size)
    }
}
