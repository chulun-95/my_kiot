package com.mykiot.pos.feature.invoice

import androidx.annotation.StringRes
import com.mykiot.pos.R

enum class InvoiceFilter { ALL, COMPLETED, CANCELLED }

@StringRes
fun InvoiceFilter.labelRes(): Int = when (this) {
    InvoiceFilter.ALL -> R.string.misc_invoice_filter_all
    InvoiceFilter.COMPLETED -> R.string.misc_invoice_filter_completed
    InvoiceFilter.CANCELLED -> R.string.misc_invoice_filter_cancelled
}

/** Map bộ lọc UI → tham số status gửi lên API (ALL = không lọc). */
fun InvoiceFilter.toStatus(): String? = when (this) {
    InvoiceFilter.ALL -> null
    InvoiceFilter.COMPLETED -> "COMPLETED"
    InvoiceFilter.CANCELLED -> "CANCELLED"
}
