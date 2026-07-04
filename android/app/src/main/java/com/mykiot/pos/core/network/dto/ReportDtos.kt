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
data class HubSummaryDto(
    @SerialName("total_products") val totalProducts: Int,
    @SerialName("low_stock_count") val lowStockCount: Int,
    @SerialName("out_of_stock_count") val outOfStockCount: Int,
    @SerialName("total_customers") val totalCustomers: Int,
    @SerialName("total_suppliers") val totalSuppliers: Int,
    @SerialName("draft_receipts_count") val draftReceiptsCount: Int,
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

@Serializable
data class RevenuePointDto(
    val period: String,
    val revenue: Double = 0.0,
    val invoices: Int = 0,
    val profit: Double = 0.0,
)

@Serializable
data class RevenueDto(
    @SerialName("total_revenue") val totalRevenue: Double = 0.0,
    @SerialName("total_profit") val totalProfit: Double = 0.0,
    val series: List<RevenuePointDto> = emptyList(),
)

@Serializable
data class TopProductItemDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String,
    val revenue: Double = 0.0,
    @SerialName("quantity_sold") val quantitySold: Double = 0.0,
    val profit: Double = 0.0,
)

@Serializable
data class TopProductsDto(
    val items: List<TopProductItemDto> = emptyList(),
)
