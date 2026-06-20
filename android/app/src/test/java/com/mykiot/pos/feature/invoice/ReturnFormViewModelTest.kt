package com.mykiot.pos.feature.invoice

import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ReturnCreateDto
import com.mykiot.pos.core.network.dto.ReturnResultDto
import com.mykiot.pos.core.network.dto.ReturnableInvoiceDto
import com.mykiot.pos.core.network.dto.ReturnableLineDto
import com.mykiot.pos.feature.invoice.data.ReturnRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test
import java.math.BigDecimal

class ReturnFormViewModelTest {
    private val repo = mockk<ReturnRepository>()
    private val res = FakeResProvider()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun returnable() = ReturnableInvoiceDto(
        invoiceId = 5, invoiceCode = "HD20260613-001", customerName = "Anh Ba",
        lines = listOf(
            ReturnableLineDto(
                invoiceItemId = 11, productId = 1, productName = "Mì Hảo Hảo", productSku = "SP1",
                unit = "gói", soldQuantity = 5.0, returnedQuantity = 0.0, returnableQuantity = 5.0, unitPrice = 4000.0,
            ),
        ),
    )

    @Test fun `load maps returnable lines`() = runTest {
        coEvery { repo.returnable(5) } returns ApiResult.Success(returnable())
        val vm = ReturnFormViewModel(repo, res)
        vm.load(5)
        testScheduler.advanceUntilIdle()
        assertEquals(1, vm.state.value.lines.size)
        assertEquals("Mì Hảo Hảo", vm.state.value.lines.first().name)
    }

    @Test fun `setQty clamps to returnable max`() = runTest {
        coEvery { repo.returnable(5) } returns ApiResult.Success(returnable())
        val vm = ReturnFormViewModel(repo, res)
        vm.load(5)
        testScheduler.advanceUntilIdle()
        vm.setQty(0, BigDecimal("99"))
        assertEquals(0, BigDecimal("5").compareTo(vm.state.value.lines.first().returnQty))
    }

    @Test fun `submit with no qty sets error and does not call create`() = runTest {
        coEvery { repo.returnable(5) } returns ApiResult.Success(returnable())
        val vm = ReturnFormViewModel(repo, res)
        vm.load(5)
        testScheduler.advanceUntilIdle()
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(R.string.misc_return_form_select_one), vm.state.value.error?.message)
        coVerify(exactly = 0) { repo.create(any()) }
    }

    @Test fun `submit posts selected lines and sets done`() = runTest {
        coEvery { repo.returnable(5) } returns ApiResult.Success(returnable())
        val body = slot<ReturnCreateDto>()
        coEvery { repo.create(capture(body)) } returns
            ApiResult.Success(ReturnResultDto(id = 9, code = "TH20260613-001", totalRefund = 8000.0, status = "COMPLETED"))
        val vm = ReturnFormViewModel(repo, res)
        vm.load(5)
        testScheduler.advanceUntilIdle()
        vm.setQty(0, BigDecimal("2"))
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertNotNull(vm.state.value.done)
        assertEquals(5, body.captured.invoiceId)
        assertEquals(1, body.captured.items.size)
        assertEquals("2", body.captured.items.first().quantity)
    }
}
