package com.mykiot.pos.core.util

import java.time.LocalDate

/** Trả (from, to) dạng "YYYY-MM-DD": 7 ngày gần nhất kể cả hôm nay. */
fun last7DaysRange(today: LocalDate = LocalDate.now()): Pair<String, String> =
    today.minusDays(6).toString() to today.toString()
