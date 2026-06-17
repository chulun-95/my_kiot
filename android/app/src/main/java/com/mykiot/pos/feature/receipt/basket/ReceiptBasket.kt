package com.mykiot.pos.feature.receipt.basket

import java.math.BigDecimal

data class ReceiptBasket(
    val lines: List<ReceiptLine> = emptyList(),
) {
    fun addScanned(line: ReceiptLine): ReceiptBasket {
        val idx = lines.indexOfFirst { it.sameItem(line) }
        return if (idx >= 0) {
            val merged = lines[idx].copy(quantity = lines[idx].quantity.add(line.quantity))
            copy(lines = lines.toMutableList().also { it[idx] = merged })
        } else {
            copy(lines = lines + line)
        }
    }

    fun setQuantity(index: Int, qty: BigDecimal): ReceiptBasket =
        mutate(index) { it.copy(quantity = qty.max(BigDecimal.ZERO)) }

    fun setCost(index: Int, cost: BigDecimal): ReceiptBasket =
        mutate(index) { it.copy(costPrice = cost.max(BigDecimal.ZERO)) }

    fun removeLine(index: Int): ReceiptBasket =
        copy(lines = lines.toMutableList().also { it.removeAt(index) })

    fun clear(): ReceiptBasket = ReceiptBasket()

    fun total(): BigDecimal = lines.fold(BigDecimal.ZERO) { acc, l -> acc.add(l.lineTotal()) }

    fun isEmpty(): Boolean = lines.isEmpty()

    /** Các dòng thực sự nhập (số lượng > 0) — bỏ qua dòng đã xoá hết số lượng. */
    fun activeLines(): List<ReceiptLine> = lines.filter { it.quantity.signum() > 0 }

    /** Có ít nhất 1 dòng số lượng > 0 để tạo phiếu nhập. */
    fun hasItems(): Boolean = lines.any { it.quantity.signum() > 0 }

    private fun mutate(index: Int, f: (ReceiptLine) -> ReceiptLine): ReceiptBasket =
        copy(lines = lines.toMutableList().also { it[index] = f(it[index]) })
}
