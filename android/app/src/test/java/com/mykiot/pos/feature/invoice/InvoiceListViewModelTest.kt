package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
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
class InvoiceListViewModelTest {

    private val repo: InvoiceListRepository = mockk(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun brief(id: Long, status: String = "COMPLETED") = InvoiceBriefDto(
        id = id, code = "HD-00$id", total = "100000",
        paidAmount = "100000", status = status,
        createdAt = "2026-06-13T10:00:00+07:00",
    )

    private fun invoiceDto(id: Long) = InvoiceDto(
        id = id, code = "HD-00$id", subtotal = "100000",
        discountAmount = "0", total = "100000", paidAmount = "100000",
        changeAmount = "0", status = "CANCELLED",
        createdAt = "2026-06-13T10:00:00+07:00", items = emptyList(),
    )

    @Test fun `load passes null status to repo`() = runTest {
        coEvery { repo.list(null) } returns ApiResult.Success(emptyList())
        val vm = InvoiceListViewModel(repo)
        vm.load()
        coVerify { repo.list(null) }
    }

    @Test fun `load populates items on success`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1), brief(2)))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        assertEquals(2, vm.state.value.items.size)
        assertFalse(vm.state.value.loading)
    }

    @Test fun `load sets errorMessage on failure`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi mạng"))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        assertEquals("Lỗi mạng", vm.state.value.errorMessage)
    }

    @Test fun `setFilter ALL shows all items`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(
            listOf(brief(1, "COMPLETED"), brief(2, "CANCELLED")),
        )
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.setFilter(InvoiceFilter.ALL)
        assertEquals(2, vm.state.value.displayedItems.size)
    }

    @Test fun `setFilter COMPLETED shows only completed`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(
            listOf(brief(1, "COMPLETED"), brief(2, "CANCELLED")),
        )
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.setFilter(InvoiceFilter.COMPLETED)
        assertEquals(1, vm.state.value.displayedItems.size)
        assertEquals("COMPLETED", vm.state.value.displayedItems.first().status)
    }

    @Test fun `setFilter CANCELLED shows only cancelled`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(
            listOf(brief(1, "COMPLETED"), brief(2, "CANCELLED")),
        )
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.setFilter(InvoiceFilter.CANCELLED)
        assertEquals(1, vm.state.value.displayedItems.size)
        assertEquals("CANCELLED", vm.state.value.displayedItems.first().status)
    }

    @Test fun `requestCancel sets cancelingId`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(emptyList())
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.requestCancel(42L)
        assertEquals(42L, vm.state.value.cancelingId)
    }

    @Test fun `dismissCancel clears cancelingId`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(emptyList())
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.requestCancel(42L)
        vm.dismissCancel()
        assertNull(vm.state.value.cancelingId)
    }

    @Test fun `cancelInvoice on success updates item status to CANCELLED`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1), brief(2)))
        coEvery { repo.cancel(1L, "Sai hàng") } returns ApiResult.Success(invoiceDto(1))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.cancelInvoice(1L, "Sai hàng")
        assertEquals("CANCELLED", vm.state.value.items.first { it.id == 1L }.status)
        assertNull(vm.state.value.cancelingId)
    }

    @Test fun `cancelInvoice on failure shows error`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Success(listOf(brief(1)))
        coEvery { repo.cancel(1L, any()) } returns ApiResult.Failure(ApiError("FORBIDDEN", "Không có quyền"))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.cancelInvoice(1L, "test")
        assertEquals("Không có quyền", vm.state.value.errorMessage)
    }

    @Test fun `clearError removes errorMessage`() = runTest {
        coEvery { repo.list(any()) } returns ApiResult.Failure(ApiError("NET", "Lỗi"))
        val vm = InvoiceListViewModel(repo)
        vm.load()
        vm.clearError()
        assertNull(vm.state.value.errorMessage)
    }
}
