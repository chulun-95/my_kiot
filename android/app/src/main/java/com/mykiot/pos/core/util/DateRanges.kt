package com.mykiot.pos.core.util

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset

/** Trả (from, to) dạng "YYYY-MM-DD": 7 ngày gần nhất kể cả hôm nay. */
fun last7DaysRange(today: LocalDate = LocalDate.now()): Pair<String, String> =
    today.minusDays(6).toString() to today.toString()

/** Trả (from, to) dạng "YYYY-MM-DD": 30 ngày gần nhất kể cả hôm nay. */
fun last30DaysRange(today: LocalDate = LocalDate.now()): Pair<String, String> =
    today.minusDays(29).toString() to today.toString()

/** Trả (from, to) dạng "YYYY-MM-DD": từ đầu tháng tới hôm nay. */
fun thisMonthRange(today: LocalDate = LocalDate.now()): Pair<String, String> =
    today.withDayOfMonth(1).toString() to today.toString()

/** "2026-06-13" → "13/06" (nhãn ngày ngắn). Trả nguyên chuỗi nếu không parse được. */
fun shortDayLabel(period: String): String {
    val parts = period.split("-")
    return if (parts.size == 3) "%02d/%02d".format(parts[2].toInt(), parts[1].toInt()) else period
}

/** "2026-06-13" → "13/06/2026" (nhãn ngày đầy đủ). */
fun fullDayLabel(period: String): String {
    val parts = period.split("-")
    return if (parts.size == 3) "%02d/%02d/%s".format(parts[2].toInt(), parts[1].toInt(), parts[0]) else period
}

/** ("2026-06-13","2026-06-20") → "13/06 – 20/06" (nhãn khoảng). */
fun rangeLabel(from: String, to: String): String = "${shortDayLabel(from)} – ${shortDayLabel(to)}"

/** epoch millis (UTC midnight từ Material DatePicker) → "YYYY-MM-DD". */
fun epochMillisToIsoDate(millis: Long): String =
    Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate().toString()
