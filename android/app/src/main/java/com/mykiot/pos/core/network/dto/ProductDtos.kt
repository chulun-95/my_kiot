package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ProductUnitDto(
    val id: Long,
    @SerialName("unit_name") val unitName: String,
    @SerialName("conversion_rate") val conversionRate: Double,
    @SerialName("sale_price") val salePrice: Double? = null,
    val barcode: String? = null,
)

@Serializable
data class ProductBriefDto(
    val id: Long,
    val sku: String,
    val barcode: String? = null,
    val name: String,
    val unit: String,
    @SerialName("sale_price") val salePrice: Double,
    @SerialName("cost_price") val costPrice: Double? = null,
    @SerialName("image_url") val imageUrl: String? = null,
    @SerialName("allow_negative") val allowNegative: Boolean = false,
    val status: String,
    val units: List<ProductUnitDto> = emptyList(),
    @SerialName("matched_unit") val matchedUnit: ProductUnitDto? = null,
    @SerialName("stock_status") val stockStatus: String? = null,
)

@Serializable
data class ProductSearchDto(val items: List<ProductBriefDto> = emptyList())

@Serializable
data class ProductListDto(
    val items: List<ProductBriefDto> = emptyList(),
    val pagination: PaginationDto? = null,
)

/** Body tạo SP mới (POST /products). Tiền gửi dạng chuỗi để tránh sai số float. */
@Serializable
data class ProductCreateDto(
    val name: String,
    val sku: String? = null,
    val barcode: String? = null,
    val unit: String = "cái",
    @SerialName("cost_price") val costPrice: String = "0",
    @SerialName("sale_price") val salePrice: String = "0",
    @SerialName("min_stock") val minStock: Int = 0,
    val status: String = "ACTIVE",
    @SerialName("allow_negative") val allowNegative: Boolean = false,
)
