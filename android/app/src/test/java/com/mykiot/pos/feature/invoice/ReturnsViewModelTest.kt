package com.mykiot.pos.feature.invoice

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
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ReturnsViewModelTest {

    private val repo: InvoiceListRepository = mockk(relaxed = true)

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun completedInvoice(id: Long) = InvoiceBriefDto(
        id = id, code = "HD-00$id", total = "100000",
        paidAmount = "100000", status = "COMPLETED",
        createdAt = "2026-06-13T10:00:00+07:00",
    )

    private fun cancelledDto(id: Long) = InvoiceDto(
        id = id, code = "HD-00$id", subtotal = "100000",
        discountAmount = "0", total = "100000", paidAmount = "100000",
        changeAmount = "0", status = "CANCELLED",
        createdAt = "2026-06-13T10:00:00+07:00", items = emptyList(),
    )

    @Test fun `load always passes COMPLETED status to repository`() = runTest {
        coEvery { repo.list("COMPLETED") } returns ApiResult.Success(emptyList())
        val vm = ReturnsViewModel(repo)
        vm.load()
        coVerify(exactly = 1) { repo.list("COMPLETED") }
    }

    @Test fun `load populates only COMPLETED invoices`() = runTest {
        coEvery { repo.list("COMPLETED") } returns ApiResult.Success(
            listOf(completedInvoice(1), completedInvoice(2)),
        )
        val vm = ReturnsViewModel(repo)
        vm.load()
        assertEquals(2, vm.state.value.items.size)
        assertEquals("COMPLETED", vm.state.value.items.first().status)
    }

    @Test fun `cancelInvoice updates item status to CANCELLED`() = runTest {
        coEvery { repo.list("COMPLETED") } returns ApiResult.Success(listOf(completedInvoice(1)))
        coEvery { repo.cancel(1L, "Khách đổi ý") } returns ApiResult.Success(cancelledDto(1))
        val vm = ReturnsViewModel(repo)
        vm.load()
        vm.cancelInvoice(1L, "Khách đổi ý")
        assertEquals("CANCELLED", vm.state.value.items.first().status)
    }
}
