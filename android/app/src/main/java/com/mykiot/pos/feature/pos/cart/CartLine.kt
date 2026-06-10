package com.mykiot.pos.feature.pos.cart

import java.math.BigDecimal

data class CartLine(
    val productId: Long,
    val unitId: Long?,            // null = đơn vị cơ bản
    val name: String,
    val sku: String,
    val unitName: String,
    val unitPrice: BigDecimal,
    val quantity: BigDecimal,
    val discount: BigDecimal = BigDecimal.ZERO,
) {
    fun lineTotal(): BigDecimal =
        (unitPrice.multiply(quantity)).subtract(discount).max(BigDecimal.ZERO)

    /** Cùng SP + cùng đơn vị → được gộp khi quét lại. */
    fun sameItem(other: CartLine): Boolean =
        productId == other.productId && unitId == other.unitId
}
