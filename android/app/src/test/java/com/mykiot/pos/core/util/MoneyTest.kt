package com.mykiot.pos.core.util

import org.junit.Assert.assertEquals
import org.junit.Test

class MoneyTest {
    @Test fun `formats VND with thousands separator and dong suffix`() {
        assertEquals("1.000 đ", formatVnd(1000))
        assertEquals("0 đ", formatVnd(0))
        assertEquals("1.234.567 đ", formatVnd(1234567))
    }

    @Test fun `formats from string decimal`() {
        assertEquals("12.500 đ", formatVnd("12500.00"))
    }
}
