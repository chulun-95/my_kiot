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
)

@Serializable
data class ProductSearchDto(val items: List<ProductBriefDto> = emptyList())
