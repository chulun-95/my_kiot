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

/**
 * Số lượng kiểu VN: bỏ số 0 thừa ở phần thập phân, dùng "," cho thập phân và "." cho hàng nghìn.
 * Backend trả DECIMAL(10,3) dạng chuỗi ("1.000" = 1.0) → KHÔNG in thô (sẽ trông như "1 nghìn").
 *   "1.000" → "1"   ·  "1.500" → "1,5"  ·  "0.300" → "0,3"  ·  "1200" → "1.200"  ·  "1200.5" → "1.200,5"
 */
fun formatQty(value: BigDecimal): String {
    val v = value.stripTrailingZeros()
    val intPart = v.toBigInteger().abs().toString()
    val grouped = intPart.reversed().chunked(3).joinToString(".").reversed()
    val scale = v.scale().coerceAtLeast(0)
    val sign = if (v.signum() < 0) "-" else ""
    if (scale == 0) return "$sign$grouped"
    // phần thập phân (đã bỏ 0 thừa) → ngăn cách bằng dấu phẩy
    val frac = v.abs().remainder(BigDecimal.ONE)
        .movePointRight(scale).toBigInteger().toString().padStart(scale, '0')
    return "$sign$grouped,$frac"
}

fun formatQty(decimalString: String): String =
    formatQty(try { BigDecimal(decimalString) } catch (_: Exception) { BigDecimal.ZERO })

/** "13/06 10:30" — ISO 8601 → múi giờ VN (+07:00). Trả "—" nếu null hoặc lỗi parse. */
fun formatDateTime(iso: String?): String {
    if (iso == null) return "—"
    return try {
        val dt = java.time.OffsetDateTime.parse(iso)
        val vn = dt.withOffsetSameInstant(java.time.ZoneOffset.ofHours(7))
        "%02d/%02d %02d:%02d".format(vn.dayOfMonth, vn.monthValue, vn.hour, vn.minute)
    } catch (_: Exception) {
        iso.take(10)
    }
}

/** "1.234" — số nguyên có dấu chấm ngăn nghìn kiểu VN, không đơn vị. */
fun formatCount(n: Int): String {
    val digits = kotlin.math.abs(n).toString().reversed().chunked(3).joinToString(".").reversed()
    val sign = if (n < 0) "-" else ""
    return "$sign$digits"
}
