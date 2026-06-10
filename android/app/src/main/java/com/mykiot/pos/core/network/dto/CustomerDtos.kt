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
data class CustomerListDto(val items: List<CustomerDto> = emptyList())
