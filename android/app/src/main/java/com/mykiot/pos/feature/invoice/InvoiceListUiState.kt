package com.mykiot.pos.feature.invoice

import com.mykiot.pos.core.network.dto.InvoiceBriefDto

enum class InvoiceFilter { ALL, COMPLETED, CANCELLED }

fun InvoiceFilter.label() = when (this) {
    InvoiceFilter.ALL -> "Tất cả"
    InvoiceFilter.COMPLETED -> "Đã bán"
    InvoiceFilter.CANCELLED -> "Đã hủy"
}

data class InvoiceListUiState(
    val loading: Boolean = false,
    val items: List<InvoiceBriefDto> = emptyList(),
    val filter: InvoiceFilter = InvoiceFilter.ALL,
    val cancelingId: Long? = null,
    val errorMessage: String? = null,
) {
    val displayedItems: List<InvoiceBriefDto>
        get() = when (filter) {
            InvoiceFilter.ALL -> items
            InvoiceFilter.COMPLETED -> items.filter { it.status == "COMPLETED" }
            InvoiceFilter.CANCELLED -> items.filter { it.status == "CANCELLED" }
        }
}
