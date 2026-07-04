package com.mykiot.pos.core.util

import org.junit.Assert.assertEquals
import org.junit.Test

class FormatCountTest {
    @Test fun `so nho hon 1000 khong co dau cham`() =
        assertEquals("87", formatCount(87))

    @Test fun `so hang nghin co dau cham ngan cach`() =
        assertEquals("1.234", formatCount(1234))

    @Test fun `so 0 tra ve dung 0`() =
        assertEquals("0", formatCount(0))

    @Test fun `so am co dau tru`() =
        assertEquals("-5", formatCount(-5))
}
