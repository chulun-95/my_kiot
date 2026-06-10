package com.mykiot.pos.feature.receipt.basket

import org.junit.Assert.assertEquals
import org.junit.Test
import java.math.BigDecimal

class ReceiptBasketTest {
    private fun line(pid: Long, qty: String, cost: String) =
        ReceiptLine(
            productId = pid, unitId = null, name = "SP$pid", sku = "SKU$pid",
            unitName = "cái", costPrice = BigDecimal(cost), quantity = BigDecimal(qty),
        )

    @Test fun `add scanned appends qty 1`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000"))
        assertEquals(1, b.lines.size)
    }

    @Test fun `scan same product increments`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000")).addScanned(line(1, "1", "8000"))
        assertEquals(1, b.lines.size)
        assertEquals(BigDecimal("2"), b.lines.first().quantity)
    }

    @Test fun `setQuantity and setCost update line`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000"))
            .setQuantity(0, BigDecimal("10")).setCost(0, BigDecimal("7500"))
        assertEquals(BigDecimal("10"), b.lines[0].quantity)
        assertEquals(BigDecimal("7500"), b.lines[0].costPrice)
    }

    @Test fun `lineTotal and total`() {
        val b = ReceiptBasket().addScanned(line(1, "10", "8000")).addScanned(line(2, "2", "5000"))
        assertEquals(BigDecimal("80000"), b.lines[0].lineTotal())
        assertEquals(BigDecimal("90000"), b.total())
    }

    @Test fun `remove drops line`() {
        val b = ReceiptBasket().addScanned(line(1, "1", "8000"))
            .addScanned(line(2, "1", "5000")).removeLine(0)
        assertEquals(1, b.lines.size)
        assertEquals(2L, b.lines.first().productId)
    }
}
