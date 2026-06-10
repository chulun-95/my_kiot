package com.mykiot.pos.feature.receipt.basket

import java.math.BigDecimal

data class ReceiptLine(
    val productId: Long,
    val unitId: Long?,
    val name: String,
    val sku: String,
    val unitName: String,
    val costPrice: BigDecimal,
    val quantity: BigDecimal,
) {
    fun lineTotal(): BigDecimal = costPrice.multiply(quantity).max(BigDecimal.ZERO)

    fun sameItem(other: ReceiptLine): Boolean =
        productId == other.productId && unitId == other.unitId
}
