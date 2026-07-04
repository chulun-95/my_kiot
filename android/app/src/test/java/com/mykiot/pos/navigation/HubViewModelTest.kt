package com.mykiot.pos.navigation

import com.mykiot.pos.R
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.HubSummaryDto
import com.mykiot.pos.feature.report.data.ReportRepository
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class HubViewModelTest {
    private val sessionManager = mockk<SessionManager>(relaxed = true)
    private val reportRepository = mockk<ReportRepository>()
    private val res = FakeResProvider()

    @Before fun setUp() {
        Dispatchers.setMain(StandardTestDispatcher())
        every { sessionManager.current } returns MutableStateFlow(null)
    }

    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `truoc khi load dung caption fallback`() = runTest {
        val vm = HubViewModel(sessionManager, reportRepository, res)
        assertEquals(
            res.get(R.string.core_hub_caption_products_fallback),
            vm.state.value.captions[Routes.PRODUCTS],
        )
    }

    @Test
    fun `load thanh cong dien so lieu that`() = runTest {
        val summary = HubSummaryDto(
            totalProducts = 1234, lowStockCount = 12, outOfStockCount = 0,
            totalCustomers = 87, totalSuppliers = 15, draftReceiptsCount = 3,
        )
        coEvery { reportRepository.hubSummary() } returns ApiResult.Success(summary)
        val vm = HubViewModel(sessionManager, reportRepository, res)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(
            res.get(R.string.core_hub_caption_products, "1.234", 12),
            vm.state.value.captions[Routes.PRODUCTS],
        )
        assertEquals(
            res.get(R.string.core_hub_caption_receipt_draft, 3),
            vm.state.value.captions[Routes.RECEIPT],
        )
    }

    @Test
    fun `load that bai giu caption fallback`() = runTest {
        coEvery { reportRepository.hubSummary() } returns ApiResult.Failure(ApiError("NETWORK_ERROR", "Lỗi mạng"))
        val vm = HubViewModel(sessionManager, reportRepository, res)
        vm.load()
        testScheduler.advanceUntilIdle()
        assertEquals(
            res.get(R.string.core_hub_caption_products_fallback),
            vm.state.value.captions[Routes.PRODUCTS],
        )
    }
}
