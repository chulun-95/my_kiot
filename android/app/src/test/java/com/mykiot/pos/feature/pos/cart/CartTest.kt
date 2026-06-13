package com.mykiot.pos.feature.pos.cart

import org.junit.Assert.assertEquals
import org.junit.Test
import java.math.BigDecimal

class CartTest {

    private fun line(pid: Long, unitId: Long?, qty: String, price: String) =
        CartLine(
            productId = pid, unitId = unitId, name = "SP$pid", sku = "SKU$pid",
            unitName = "cái", unitPrice = BigDecimal(price), quantity = BigDecimal(qty),
        )

    @Test fun `add scanned product appends with qty 1`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
        assertEquals(1, cart.lines.size)
        assertEquals(BigDecimal("1"), cart.lines.first().quantity)
    }

    @Test fun `scanning same product and unit again increments qty`() {
        val cart = Cart()
            .addScanned(line(1, null, "1", "10000"))
            .addScanned(line(1, null, "1", "10000"))
        assertEquals(1, cart.lines.size)
        assertEquals(BigDecimal("2"), cart.lines.first().quantity)
    }

    @Test fun `same product different unit creates separate line`() {
        val cart = Cart()
            .addScanned(line(1, null, "1", "10000"))
            .addScanned(line(1, 5, "1", "240000"))
        assertEquals(2, cart.lines.size)
    }

    @Test fun `setQuantity replaces and supports decimals for weighed goods`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
            .setQuantity(0, BigDecimal("1.5"))
        assertEquals(BigDecimal("1.5"), cart.lines.first().quantity)
    }

    @Test fun `removeLine drops it`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
            .addScanned(line(2, null, "1", "5000"))
            .removeLine(0)
        assertEquals(1, cart.lines.size)
        assertEquals(2L, cart.lines.first().productId)
    }

    @Test fun `lineTotal = qty x price - discount, subtotal sums lines`() {
        val cart = Cart()
            .addScanned(line(1, null, "2", "10000"))        // 20000
            .addScanned(line(2, null, "1", "5000"))         // 5000
            .setLineDiscount(0, BigDecimal("2000"))         // 18000
        assertEquals(BigDecimal("18000"), cart.lines[0].lineTotal())
        assertEquals(BigDecimal("23000"), cart.subtotal())
    }

    @Test fun `total applies invoice-level discount, never below zero`() {
        val cart = Cart()
            .addScanned(line(1, null, "1", "10000"))
            .withInvoiceDiscount(BigDecimal("3000"))
        assertEquals(BigDecimal("7000"), cart.total())
    }

    @Test fun `changeAmount = paid - total clamped at zero`() {
        val cart = Cart().addScanned(line(1, null, "1", "10000"))
        assertEquals(BigDecimal("5000"), cart.changeFor(BigDecimal("15000")))
        assertEquals(BigDecimal.ZERO, cart.changeFor(BigDecimal("8000")))
    }
}
