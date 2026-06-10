package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DashboardDto(
    @SerialName("today_revenue") val todayRevenue: String,
    @SerialName("today_invoices") val todayInvoices: Int,
    @SerialName("today_profit") val todayProfit: String? = null,
    @SerialName("today_customers") val todayCustomers: Int,
    @SerialName("pending_drafts") val pendingDrafts: Int,
    @SerialName("low_stock_count") val lowStockCount: Int,
    @SerialName("out_of_stock_count") val outOfStockCount: Int,
    @SerialName("inventory_value") val inventoryValue: String? = null,
)

@Serializable
data class EodMethodRowDto(
    val method: String,
    val opening: String,
    @SerialName("total_in") val totalIn: String,
    @SerialName("total_out") val totalOut: String,
    val closing: String,
)

@Serializable
data class EndOfDayDto(
    @SerialName("business_date") val businessDate: String,
    @SerialName("by_method") val byMethod: List<EodMethodRowDto> = emptyList(),
    @SerialName("opening_total") val openingTotal: String,
    @SerialName("in_total") val inTotal: String,
    @SerialName("out_total") val outTotal: String,
    @SerialName("closing_total") val closingTotal: String,
    @SerialName("sales_revenue") val salesRevenue: String,
    @SerialName("sales_invoices") val salesInvoices: Int,
)
