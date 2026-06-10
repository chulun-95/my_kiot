package com.mykiot.pos.feature.pos.cart

import java.math.BigDecimal

data class Cart(
    val lines: List<CartLine> = emptyList(),
    val invoiceDiscount: BigDecimal = BigDecimal.ZERO,
) {
    fun addScanned(line: CartLine): Cart {
        val idx = lines.indexOfFirst { it.sameItem(line) }
        return if (idx >= 0) {
            val merged = lines[idx].copy(quantity = lines[idx].quantity.add(line.quantity))
            copy(lines = lines.toMutableList().also { it[idx] = merged })
        } else {
            copy(lines = lines + line)
        }
    }

    fun setQuantity(index: Int, qty: BigDecimal): Cart =
        mutate(index) { it.copy(quantity = qty.max(BigDecimal.ZERO)) }

    fun setUnitPrice(index: Int, price: BigDecimal): Cart =
        mutate(index) { it.copy(unitPrice = price.max(BigDecimal.ZERO)) }

    fun setLineDiscount(index: Int, discount: BigDecimal): Cart =
        mutate(index) { it.copy(discount = discount.max(BigDecimal.ZERO)) }

    fun removeLine(index: Int): Cart =
        copy(lines = lines.toMutableList().also { it.removeAt(index) })

    fun withInvoiceDiscount(discount: BigDecimal): Cart =
        copy(invoiceDiscount = discount.max(BigDecimal.ZERO))

    fun clear(): Cart = Cart()

    fun subtotal(): BigDecimal =
        lines.fold(BigDecimal.ZERO) { acc, l -> acc.add(l.lineTotal()) }

    fun total(): BigDecimal = subtotal().subtract(invoiceDiscount).max(BigDecimal.ZERO)

    fun changeFor(paid: BigDecimal): BigDecimal = paid.subtract(total()).max(BigDecimal.ZERO)

    fun isEmpty(): Boolean = lines.isEmpty()

    private fun mutate(index: Int, f: (CartLine) -> CartLine): Cart =
        copy(lines = lines.toMutableList().also { it[index] = f(it[index]) })
}
