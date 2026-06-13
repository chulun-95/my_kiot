package com.mykiot.pos.core.util

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDate

class DateRangesTest {
    @Test fun `last7DaysRange spans 6 days back to today inclusive`() {
        val today = LocalDate.of(2026, 6, 13)
        val (from, to) = last7DaysRange(today)
        assertEquals("2026-06-07", from)
        assertEquals("2026-06-13", to)
    }
}
