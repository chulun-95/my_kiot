package com.mykiot.pos.feature.pos

import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.pos.cart.Cart
import com.mykiot.pos.feature.pos.data.CustomerLite

data class PosUiState(
    val cart: Cart = Cart(),
    val query: String = "",
    val searchResults: List<ProductBriefDto> = emptyList(),
    val customer: CustomerLite? = null,
    // ----- Chọn khách hàng -----
    val showCustomerPicker: Boolean = false,
    val customerResults: List<CustomerLite> = emptyList(),
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val infoMessage: String? = null,       // thông báo ngắn (vd: "Đã treo đơn")
    val lastInvoiceCode: String? = null,   // set sau khi checkout thành công → trigger in
    val lastInvoice: InvoiceDto? = null,   // chi tiết hoá đơn để render bill
    // ----- Giỏ hàng chờ (hoá đơn treo) -----
    val heldDraftId: Long? = null,         // != null = giỏ hiện tại đang sửa từ 1 đơn treo
    val drafts: List<InvoiceBriefDto> = emptyList(),
    val showDrafts: Boolean = false,
)
