package com.mykiot.pos.core.util

import java.math.BigDecimal
import java.math.RoundingMode

/** "1.234.567 đ" — dấu chấm ngăn nghìn, kiểu VN. */
fun formatVnd(amount: Long): String {
    val digits = kotlin.math.abs(amount).toString().reversed().chunked(3).joinToString(".").reversed()
    val sign = if (amount < 0) "-" else ""
    return "$sign$digits đ"
}

fun formatVnd(decimalString: String): String =
    formatVnd(BigDecimal(decimalString).setScale(0, RoundingMode.HALF_UP).toLong())

fun formatVnd(amount: BigDecimal): String =
    formatVnd(amount.setScale(0, RoundingMode.HALF_UP).toLong())
