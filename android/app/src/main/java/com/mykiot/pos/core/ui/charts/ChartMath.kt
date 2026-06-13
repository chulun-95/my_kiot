package com.mykiot.pos.core.ui.charts

/** Hàm thuần tính tỉ lệ cho biểu đồ — tách khỏi Canvas để test. */
object ChartMath {
    /** Mỗi giá trị / max → [0f,1f]. max<=0 → tất cả 0f. */
    fun normalize(values: List<Double>): List<Float> {
        val max = values.maxOrNull() ?: 0.0
        if (max <= 0.0) return values.map { 0f }
        return values.map { (it / max).toFloat() }
    }

    /** Chia 360° theo tỉ trọng. total<=0 → tất cả 0f. */
    fun sweepAngles(values: List<Double>): List<Float> {
        val total = values.sum()
        if (total <= 0.0) return values.map { 0f }
        return values.map { (it / total * 360.0).toFloat() }
    }
}
