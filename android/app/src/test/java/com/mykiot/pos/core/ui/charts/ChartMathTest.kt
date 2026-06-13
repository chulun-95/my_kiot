package com.mykiot.pos.core.ui.charts

import org.junit.Assert.assertEquals
import org.junit.Test

class ChartMathTest {
    @Test fun `normalize divides by max`() {
        val r = ChartMath.normalize(listOf(0.0, 5.0, 10.0))
        assertEquals(0.0f, r[0], 0.0001f)
        assertEquals(0.5f, r[1], 0.0001f)
        assertEquals(1.0f, r[2], 0.0001f)
    }

    @Test fun `normalize all zero when max is zero`() {
        val r = ChartMath.normalize(listOf(0.0, 0.0))
        assertEquals(0.0f, r[0], 0.0001f)
        assertEquals(0.0f, r[1], 0.0001f)
    }

    @Test fun `sweepAngles split 360 by share`() {
        val r = ChartMath.sweepAngles(listOf(1.0, 3.0))
        assertEquals(90.0f, r[0], 0.0001f)
        assertEquals(270.0f, r[1], 0.0001f)
    }

    @Test fun `sweepAngles all zero when total is zero`() {
        val r = ChartMath.sweepAngles(listOf(0.0, 0.0))
        assertEquals(0.0f, r[0], 0.0001f)
    }
}
