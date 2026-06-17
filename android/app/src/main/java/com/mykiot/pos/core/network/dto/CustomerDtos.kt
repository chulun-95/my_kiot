package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CustomerDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    @SerialName("total_spent") val totalSpent: Double = 0.0,
    @SerialName("total_orders") val totalOrders: Int = 0,
)

@Serializable
data class CustomerListDto(
    val items: List<CustomerDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

/** Khớp CustomerResponse ở backend (GET /customers/{id}.customer, POST /customers). */
@Serializable
data class CustomerResponseDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    val note: String? = null,
    @SerialName("total_spent") val totalSpent: Double = 0.0,
    @SerialName("total_orders") val totalOrders: Int = 0,
    @SerialName("last_order_at") val lastOrderAt: String? = null,
)

/** 1 dòng lịch sử mua — khớp CustomerOrderHistoryItem. */
@Serializable
data class CustomerOrderHistoryDto(
    @SerialName("invoice_id") val invoiceId: Long,
    val code: String,
    val total: Double = 0.0,
    @SerialName("completed_at") val completedAt: String? = null,
    val status: String,
)

/** Khớp CustomerDetailResponse: { customer, recent_orders }. */
@Serializable
data class CustomerDetailDto(
    val customer: CustomerResponseDto,
    @SerialName("recent_orders") val recentOrders: List<CustomerOrderHistoryDto> = emptyList(),
)

@Serializable
data class CustomerCreateDto(
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    val note: String? = null,
)
