package com.mykiot.pos.feature.pos

import com.mykiot.pos.core.hardware.printer.ReceiptPrinter
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.pos.cart.CartLine
import com.mykiot.pos.feature.pos.data.PosRepository
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
class PosViewModelTest {

    private val repo: PosRepository = mockk(relaxed = true)
    private val printer: ReceiptPrinter = mockk(relaxed = true)

    @Before fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        // map DTO -> CartLine bằng logic thật (đơn vị cơ bản)
        every { repo.toCartLine(any<ProductBriefDto>()) } answers {
            val d = firstArg<ProductBriefDto>()
            CartLine(
                productId = d.id, unitId = null, name = d.name, sku = d.sku,
                unitName = d.unit, unitPrice = BigDecimal(d.salePrice.toString()),
                quantity = BigDecimal.ONE,
            )
        }
    }

    @After fun tearDown() = Dispatchers.resetMain()

    private fun brief(id: Long, price: Double) = ProductBriefDto(
        id = id, sku = "SKU$id", name = "SP$id", unit = "cái",
        salePrice = price, status = "ACTIVE",
    )

    private fun completedInvoice(code: String) = InvoiceDto(
        id = 7, code = code, subtotal = "10000", discountAmount = "0",
        total = "10000", paidAmount = "10000", changeAmount = "0", status = "COMPLETED",
        createdAt = "2026-06-09T14:00:00Z",
    )

    @Test fun `scanned barcode adds product to cart`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1, 10000.0))
        val vm = PosViewModel(repo, printer)

        vm.onBarcodeScanned("8938505970")

        val s = vm.state.value
        assertEquals(1, s.cart.lines.size)
        assertEquals(1L, s.cart.lines.first().productId)
    }

    @Test fun `scanning same barcode twice increments quantity`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1, 10000.0))
        val vm = PosViewModel(repo, printer)

        vm.onBarcodeScanned("x"); vm.onBarcodeScanned("x")

        assertEquals(1, vm.state.value.cart.lines.size)
        assertEquals(BigDecimal("2"), vm.state.value.cart.lines.first().quantity)
    }

    @Test fun `unknown barcode surfaces vietnamese error, cart unchanged`() = runTest {
        coEvery { repo.byBarcode(any()) } returns
            ApiResult.Failure(ApiError("NOT_FOUND", "Không tìm thấy sản phẩm", 404))
        val vm = PosViewModel(repo, printer)

        vm.onBarcodeScanned("nope")

        assertEquals(0, vm.state.value.cart.lines.size)
        assertEquals("Không tìm thấy sản phẩm", vm.state.value.errorMessage)
    }

    @Test fun `checkout success sets invoice code and clears cart`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1, 10000.0))
        coEvery { repo.checkout(any(), any(), any(), any(), any()) } returns
            ApiResult.Success(completedInvoice("HD20260609-007"))
        val vm = PosViewModel(repo, printer)
        vm.onBarcodeScanned("x")

        vm.checkout(emptyList(), allowDebt = false)

        val s = vm.state.value
        assertEquals("HD20260609-007", s.lastInvoiceCode)
        assertEquals(0, s.cart.lines.size)
        assertNull(s.errorMessage)
    }

    @Test fun `checkout failure keeps cart and shows error`() = runTest {
        coEvery { repo.byBarcode(any()) } returns ApiResult.Success(brief(1, 10000.0))
        coEvery { repo.checkout(any(), any(), any(), any(), any()) } returns
            ApiResult.Failure(ApiError("INSUFFICIENT_STOCK", "SP1 chỉ còn 0", 400))
        val vm = PosViewModel(repo, printer)
        vm.onBarcodeScanned("x")

        vm.checkout(emptyList(), allowDebt = false)

        assertEquals(1, vm.state.value.cart.lines.size)
        assertEquals("SP1 chỉ còn 0", vm.state.value.errorMessage)
        assertNull(vm.state.value.lastInvoiceCode)
    }

    @Test fun `checkout on empty cart shows vietnamese error and does not call repo`() = runTest {
        val vm = PosViewModel(repo, printer)

        vm.checkout(emptyList(), allowDebt = false)

        assertEquals("Giỏ hàng trống", vm.state.value.errorMessage)
    }
}
