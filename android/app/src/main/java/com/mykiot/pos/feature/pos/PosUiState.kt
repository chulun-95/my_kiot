package com.mykiot.pos.feature.pos

import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.pos.cart.Cart
import com.mykiot.pos.feature.pos.data.CustomerLite

data class PosUiState(
    val cart: Cart = Cart(),
    val query: String = "",
    val searchResults: List<ProductBriefDto> = emptyList(),
    val customer: CustomerLite? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val lastInvoiceCode: String? = null,   // set sau khi checkout thành công → trigger in
    val lastInvoice: InvoiceDto? = null,   // chi tiết hoá đơn để render bill
)
