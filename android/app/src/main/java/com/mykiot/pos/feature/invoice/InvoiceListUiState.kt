package com.mykiot.pos.feature.invoice

enum class InvoiceFilter { ALL, COMPLETED, CANCELLED }

fun InvoiceFilter.label() = when (this) {
    InvoiceFilter.ALL -> "Tất cả"
    InvoiceFilter.COMPLETED -> "Đã bán"
    InvoiceFilter.CANCELLED -> "Đã hủy"
}

/** Map bộ lọc UI → tham số status gửi lên API (ALL = không lọc). */
fun InvoiceFilter.toStatus(): String? = when (this) {
    InvoiceFilter.ALL -> null
    InvoiceFilter.COMPLETED -> "COMPLETED"
    InvoiceFilter.CANCELLED -> "CANCELLED"
}
