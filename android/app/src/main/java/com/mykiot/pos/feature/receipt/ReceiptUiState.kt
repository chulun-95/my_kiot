package com.mykiot.pos.feature.receipt

import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.feature.receipt.basket.ReceiptBasket
import com.mykiot.pos.feature.receipt.data.SupplierLite

data class ReceiptUiState(
    val basket: ReceiptBasket = ReceiptBasket(),
    val query: String = "",
    val searchResults: List<ProductBriefDto> = emptyList(),
    val suppliers: List<SupplierDto> = emptyList(),
    val supplier: SupplierLite? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val lastReceiptCode: String? = null,
)
