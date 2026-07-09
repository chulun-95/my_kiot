package com.mykiot.pos.core.auth

import java.time.Instant
import java.time.OffsetDateTime

data class CurrentUser(
    val id: Long,
    val fullName: String,
    val role: String,    // "OWNER" | "CASHIER"
    val tenantId: Long,
    val tenantName: String,
    val expiresAt: Instant? = null,   // hạn dùng gói dịch vụ của tenant; null = không giới hạn
)

/** Parse chuỗi ISO 8601 có offset (vd "2026-07-01T00:00:00+00:00") từ backend; null nếu thiếu/lỗi. */
fun parseExpiresAt(iso: String?): Instant? {
    if (iso.isNullOrBlank()) return null
    return runCatching { OffsetDateTime.parse(iso).toInstant() }.getOrNull()
}
