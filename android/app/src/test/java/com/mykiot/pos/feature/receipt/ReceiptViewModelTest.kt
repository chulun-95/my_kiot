package com.mykiot.pos.feature.receipt

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.GoodsReceiptDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.receipt.basket.ReceiptLine
import com.mykiot.pos.feature.receipt.data.ReceiptRepository
import io.mockk.coEvery
import io.mockk.every
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
import java.math.BigDecimal

@OptIn(ExperimentalCoroutinesApi::class)
class ReceiptViewModelTest {

    private val repo: ReceiptRepository = mockk(relaxed = true)

    @Before fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        every { repo.toReceiptLine(any()) } answers {
            val d = firstArg<ProductBriefDto>()
            ReceiptLine(
                productId = d.id, unitId = null, name = d.name, sku = d.sku,
                unitName = d.unit, costPrice = BigDecimal((d.costPrice ?: 0.0).toString()),
                quantity = BigDecimal.ONE,
            )
        }
    }

    @After fun tearDown() = Dispatchers.resetMain()

    private fun brief(id: Long) = ProductBriefDto(
        id = id, sku = "SKU$id", name = "SP$id", unit = "cái", salePrice = 10000.0,
        costPrice = 8000.0, status = "ACTIVE",
    )

    private fun receipt(code: String) = GoodsReceiptDto(
        id = 3, code = code, total = "80000", paidAmount = "0", status = "COMPLETED",
        createdAt = "2026-06-09T14:00:00Z",
    )

    @Test fun `scan adds product to basket`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1))
        val vm = ReceiptViewModel(repo)

        vm.onBarcodeScanned("x")

        assertEquals(1, vm.state.value.basket.lines.size)
        assertEquals(BigDecimal("8000"), vm.state.value.basket.lines.first().costPrice)
    }

    @Test fun `submit success clears basket and sets receipt code`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1))
        coEvery { repo.submit(any(), any(), any(), any()) } returns ApiResult.Success(receipt("NK20260609-003"))
        val vm = ReceiptViewModel(repo)
        vm.onBarcodeScanned("x")

        vm.submit(BigDecimal.ZERO, "CASH")

        assertEquals("NK20260609-003", vm.state.value.lastReceiptCode)
        assertEquals(0, vm.state.value.basket.lines.size)
        assertNull(vm.state.value.errorMessage)
    }

    @Test fun `submit failure keeps basket and shows error`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1))
        coEvery { repo.submit(any(), any(), any(), any()) } returns
            ApiResult.Failure(ApiError("VALIDATION", "Giá vốn không hợp lệ", 400))
        val vm = ReceiptViewModel(repo)
        vm.onBarcodeScanned("x")

        vm.submit(BigDecimal.ZERO, "CASH")

        assertEquals(1, vm.state.value.basket.lines.size)
        assertEquals("Giá vốn không hợp lệ", vm.state.value.errorMessage)
        assertNull(vm.state.value.lastReceiptCode)
    }

    @Test fun `submit on empty basket shows vietnamese error`() = runTest {
        val vm = ReceiptViewModel(repo)

        vm.submit(BigDecimal.ZERO, "CASH")

        assertEquals("Phiếu nhập trống", vm.state.value.errorMessage)
    }
}
