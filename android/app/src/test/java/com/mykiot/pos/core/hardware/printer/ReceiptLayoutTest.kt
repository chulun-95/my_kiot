package com.mykiot.pos.core.hardware.printer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ReceiptLayoutTest {

    private val data = ReceiptData(
        shopName = "TAP HOA ABC",
        shopPhone = "0901234567",
        invoiceCode = "HD20260609-001",
        dateTime = "09/06/2026 21:30",
        lines = listOf(
            ReceiptItemLine("Mi tom Hao Hao", qty = "2", unitPrice = "4.000", lineTotal = "8.000"),
            ReceiptItemLine("Nuoc ngot Coca 330ml", qty = "1", unitPrice = "10.000", lineTotal = "10.000"),
        ),
        total = "18.000 đ",
        paid = "20.000 đ",
        change = "2.000 đ",
        footer = "Cam on quy khach!",
    )

    @Test fun `every rendered line fits 32 chars`() {
        ReceiptLayout.render(data, width = 32).forEach {
            assertTrue("Quá dài: '$it' (${it.length})", it.length <= 32)
        }
    }

    @Test fun `contains shop name, code and total`() {
        val text = ReceiptLayout.render(data, width = 32).joinToString("\n")
        assertTrue(text.contains("TAP HOA ABC"))
        assertTrue(text.contains("HD20260609-001"))
        assertTrue(text.contains("18.000 đ"))
        assertTrue(text.contains("Cam on quy khach!"))
    }

    @Test fun `right-aligns total amount on its own row`() {
        val totalRow = ReceiptLayout.render(data, width = 32).first { it.contains("TONG") }
        assertEquals(32, totalRow.length)
        assertTrue(totalRow.trimEnd().endsWith("18.000 đ"))
    }
}
