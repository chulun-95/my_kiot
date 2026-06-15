package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** 1 dòng có thể trả của hóa đơn — khớp ReturnableLine (backend). */
@Serializable
data class ReturnableLineDto(
    @SerialName("invoice_item_id") val invoiceItemId: Long,
    @SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String,
    @SerialName("product_sku") val productSku: String,
    val unit: String? = null,
    @SerialName("sold_quantity") val soldQuantity: Double = 0.0,
    @SerialName("returned_quantity") val returnedQuantity: Double = 0.0,
    @SerialName("returnable_quantity") val returnableQuantity: Double = 0.0,
    @SerialName("unit_price") val unitPrice: Double = 0.0,
)

/** Khớp ReturnableInvoiceResponse. */
@Serializable
data class ReturnableInvoiceDto(
    @SerialName("invoice_id") val invoiceId: Long,
    @SerialName("invoice_code") val invoiceCode: String,
    @SerialName("customer_id") val customerId: Long? = null,
    @SerialName("customer_name") val customerName: String? = null,
    val lines: List<ReturnableLineDto> = emptyList(),
)

@Serializable
data class ReturnItemInputDto(
    @SerialName("invoice_item_id") val invoiceItemId: Long,
    val quantity: String,                       // Decimal as string để tránh sai số
)

/** Body POST /returns — khớp ReturnCreateRequest. */
@Serializable
data class ReturnCreateDto(
    @SerialName("invoice_id") val invoiceId: Long,
    val items: List<ReturnItemInputDto> = emptyList(),
    @SerialName("refund_method") val refundMethod: String = "CASH",  // CASH | BANK_TRANSFER | EWALLET
    val reason: String? = null,
)

/** Kết quả tạo phiếu trả (subset ReturnResponse). */
@Serializable
data class ReturnResultDto(
    val id: Long,
    val code: String,
    @SerialName("total_refund") val totalRefund: Double = 0.0,
    val status: String,
)
