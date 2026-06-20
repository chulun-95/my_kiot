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
