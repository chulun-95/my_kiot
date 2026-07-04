package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SupplierDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    @SerialName("total_debt") val totalDebt: Double = 0.0,
)

@Serializable
data class SupplierListDto(
    val items: List<SupplierDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

@Serializable
data class SupplierResponseDto(
    val id: Long,
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    @SerialName("tax_code") val taxCode: String? = null,
    val note: String? = null,
    @SerialName("total_debt") val totalDebt: Double = 0.0,
)

/** Body tạo NCC mới (POST /suppliers). */
@Serializable
data class SupplierCreateDto(
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    @SerialName("tax_code") val taxCode: String? = null,
    val note: String? = null,
)

@Serializable
data class GoodsReceiptItemInputDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("unit_id") val unitId: Long? = null,
    val quantity: String,
    @SerialName("cost_price") val costPrice: String,
)

@Serializable
data class GoodsReceiptCreateDto(
    @SerialName("supplier_id") val supplierId: Long? = null,
    val items: List<GoodsReceiptItemInputDto>,
    @SerialName("paid_amount") val paidAmount: String = "0",
    @SerialName("payment_method") val paymentMethod: String = "CASH",
    val note: String? = null,
)

@Serializable
data class GoodsReceiptItemDto(
    val id: Long,
    @SerialName("product_id") val productId: Long,
    @SerialName("product_name") val productName: String? = null,
    @SerialName("product_sku") val productSku: String? = null,
    @SerialName("unit_id") val unitId: Long? = null,
    @SerialName("unit_name") val unitName: String? = null,
    val quantity: String,
    @SerialName("cost_price") val costPrice: String,
    @SerialName("line_total") val lineTotal: String,
)

@Serializable
data class GoodsReceiptDto(
    val id: Long,
    val code: String,
    @SerialName("supplier_id") val supplierId: Long? = null,
    @SerialName("supplier_name") val supplierName: String? = null,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    val items: List<GoodsReceiptItemDto> = emptyList(),
)

// ---- Phase 4: inventory & kardex ----

@Serializable
data class UnitBreakdownDto(
    @SerialName("unit_name") val unitName: String,
    @SerialName("conversion_rate") val conversionRate: Double,
    @SerialName("quantity_in_unit") val quantityInUnit: String,
)

@Serializable
data class InventoryItemDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("product_sku") val productSku: String,
    @SerialName("product_name") val productName: String,
    val unit: String,
    val quantity: String,
    @SerialName("min_stock") val minStock: Int,
    @SerialName("cost_price") val costPrice: String? = null,
    @SerialName("sale_price") val salePrice: String,
    @SerialName("units_breakdown") val unitsBreakdown: List<UnitBreakdownDto> = emptyList(),
)

@Serializable
data class PaginationDto(
    val page: Int,
    val limit: Int,
    val total: Int,
    @SerialName("total_pages") val totalPages: Int,
)

@Serializable
data class InventoryListDto(
    val items: List<InventoryItemDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

/** 1 dòng cảnh báo hàng sắp/hết — shape riêng của GET /inventory/low-stock
 *  (KHÁC InventoryItemDto: có severity + shortage, không có giá). */
@Serializable
data class LowStockItemDto(
    @SerialName("product_id") val productId: Long,
    @SerialName("product_sku") val productSku: String,
    @SerialName("product_name") val productName: String,
    val unit: String,
    val quantity: String,
    @SerialName("min_stock") val minStock: Int,
    val severity: String,            // OUT_OF_STOCK | LOW
    val shortage: String,
)

@Serializable
data class LowStockSummaryDto(
    @SerialName("out_of_stock_count") val outOfStockCount: Int = 0,
    @SerialName("low_count") val lowCount: Int = 0,
    @SerialName("total_count") val totalCount: Int = 0,
)

@Serializable
data class LowStockDto(
    val items: List<LowStockItemDto> = emptyList(),
    val summary: LowStockSummaryDto? = null,
)

@Serializable
data class StockMovementDto(
    val id: Long,
    val quantity: String,
    @SerialName("unit_cost") val unitCost: String? = null,
    val type: String,
    @SerialName("ref_type") val refType: String,
    @SerialName("ref_id") val refId: Long,
    @SerialName("balance_after") val balanceAfter: String,
    val note: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class StockMovementsDto(val items: List<StockMovementDto> = emptyList())

@Serializable
data class GoodsReceiptBriefDto(
    val id: Long,
    val code: String,
    @SerialName("supplier_id") val supplierId: Long? = null,
    @SerialName("supplier_name") val supplierName: String? = null,
    val total: String,
    @SerialName("paid_amount") val paidAmount: String,
    val status: String,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class GoodsReceiptListDto(
    val items: List<GoodsReceiptBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)
