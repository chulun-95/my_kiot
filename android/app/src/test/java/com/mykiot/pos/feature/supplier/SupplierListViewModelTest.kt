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
