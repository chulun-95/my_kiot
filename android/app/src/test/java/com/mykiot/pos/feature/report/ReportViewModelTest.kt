package com.mykiot.pos.feature.report

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto
import com.mykiot.pos.feature.report.data.ReportRepository
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
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ReportViewModelTest {

    private val repo: ReportRepository = mockk(relaxed = true)
    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun dashboard() = DashboardDto(
        todayRevenue = "1500000", todayInvoices = 12, todayCustomers = 8,
        pendingDrafts = 1, lowStockCount = 3, outOfStockCount = 1,
    )

    private fun eod() = EndOfDayDto(
        businessDate = "2026-06-09", openingTotal = "0", inTotal = "1500000",
        outTotal = "0", closingTotal = "1500000", salesRevenue = "1500000", salesInvoices = 12,
    )

    @Test fun `load dashboard and eod for owner`() = runTest {
        coEvery { repo.dashboard() } returns ApiResult.Success(dashboard())
        coEvery { repo.endOfDay() } returns ApiResult.Success(eod())
        val vm = ReportViewModel(repo)

        vm.load()

        assertEquals(12, vm.state.value.dashboard?.todayInvoices)
        assertEquals("1500000", vm.state.value.eod?.closingTotal)
        assertEquals(false, vm.state.value.loading)
    }

    @Test fun `dashboard failure shows vietnamese error`() = runTest {
        coEvery { repo.dashboard() } returns ApiResult.Failure(ApiError("SERVER", "Lỗi máy chủ", 500))
        coEvery { repo.endOfDay() } returns ApiResult.Failure(ApiError("FORBIDDEN", "x", 403))
        val vm = ReportViewModel(repo)

        vm.load()

        assertEquals("Lỗi máy chủ", vm.state.value.errorMessage)
    }

    @Test fun `eod forbidden for cashier is silently hidden`() = runTest {
        coEvery { repo.dashboard() } returns ApiResult.Success(dashboard())
        coEvery { repo.endOfDay() } returns ApiResult.Failure(ApiError("FORBIDDEN", "Không có quyền", 403))
        val vm = ReportViewModel(repo)

        vm.load()

        assertNull(vm.state.value.eod)
        assertNull(vm.state.value.errorMessage)
        assertEquals(12, vm.state.value.dashboard?.todayInvoices)
    }

    @Test fun `revenue and top products loaded for owner`() = runTest {
        coEvery { repo.dashboard() } returns ApiResult.Success(dashboard())
        coEvery { repo.revenueRange(any(), any()) } returns ApiResult.Success(
            RevenueDto(totalRevenue = 500000.0, series = emptyList()),
        )
        coEvery { repo.topProducts(any()) } returns ApiResult.Success(TopProductsDto(items = emptyList()))
        val vm = ReportViewModel(repo)

        vm.load()

        assertEquals(500000.0, vm.state.value.revenue?.totalRevenue ?: 0.0, 0.001)
        assertEquals(0, vm.state.value.topProducts?.items?.size)
    }

    @Test fun `revenue and top products hidden for cashier 403`() = runTest {
        coEvery { repo.dashboard() } returns ApiResult.Success(dashboard())
        coEvery { repo.revenueRange(any(), any()) } returns ApiResult.Failure(ApiError("FORBIDDEN", "x", 403))
        coEvery { repo.topProducts(any()) } returns ApiResult.Failure(ApiError("FORBIDDEN", "x", 403))
        val vm = ReportViewModel(repo)

        vm.load()

        assertNull(vm.state.value.revenue)
        assertNull(vm.state.value.topProducts)
    }
}
