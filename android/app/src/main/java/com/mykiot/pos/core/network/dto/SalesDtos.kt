package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class InvoiceItemInputDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("unit_id") val unitId: Long? = null,
    val quantity: String,                       // Decimal as string để tránh sai số
    @SerialName("unit_price") val unitPrice: String? = null,
    @SerialName("discount_amount") val discountAmount: String = "0",
)

@Serializable
data class InvoiceCreateDto(
    @SerialName("customer_id") val customerId: Long? = null,
    val items: List<InvoiceItemInputDto> = emptyList(),
    @SerialName("discount_amount") val discountAmount: String = "0",
    val note: String? = null,
)

@Serializable
data class PaymentInputDto(
    val method: String,                         // CASH | BANK_TRANSFER | MOMO | VNPAY | OTHER
    val amount: String,
    val note: String? = null,
)

@Serializable
data class InvoiceCompleteDto(
    val payments: List<PaymentInputDto> = emptyList(),
    @SerialName("allow_debt") val allowDebt: Boolean = false,
)

@Serializable
data class InvoiceItemDto(
    val id: Long,
    @SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String,
    @SerialName("product_sku") val productSku: String,
    val unit: String? = null,
    @SerialName("unit_id") val unitId: Long? = null,
    val quantity: String,
    @SerialName("unit_price") val unitPrice: String,
    @SerialName("discount_amount") val discountAmount: String,
    @SerialName("line_total") val lineTotal: String,
)

@Serializable
data class InvoiceDto(
    val id: Long,
    val code: String,
    @SerialName("customer_id") val customerId: Long? = null,
    @SerialName("customer_name") val customerName: String? = null,
    val subtotal: String,
    @SerialName("discount_amount") val discountAmount: String,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    @SerialName("change_amount") val changeAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    val items: List<InvoiceItemDto> = emptyList(),
)

@Serializable
data class InvoiceBriefDto(
    val id: Long,
    val code: String,
    @SerialName("customer_name") val customerName: String? = null,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class InvoiceDraftListDto(val items: List<InvoiceBriefDto> = emptyList())

@Serializable
data class InvoiceListDto(
    val items: List<InvoiceBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

@Serializable
data class CancelInvoiceDto(val reason: String)
