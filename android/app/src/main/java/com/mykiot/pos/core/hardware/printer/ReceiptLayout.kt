package com.mykiot.pos.core.hardware.printer

data class ReceiptItemLine(
    val name: String,
    val qty: String,
    val unitPrice: String,
    val lineTotal: String,
)

data class ReceiptData(
    val shopName: String,
    val shopPhone: String?,
    val invoiceCode: String,
    val dateTime: String,
    val lines: List<ReceiptItemLine>,
    val total: String,
    val paid: String,
    val change: String,
    val footer: String?,
)

object ReceiptLayout {

    fun render(data: ReceiptData, width: Int = 32): List<String> {
        val out = mutableListOf<String>()
        out += center(data.shopName, width)
        data.shopPhone?.let { out += center("DT: $it", width) }
        out += "-".repeat(width)
        out += data.invoiceCode
        out += data.dateTime
        out += "-".repeat(width)
        data.lines.forEach { item ->
            // dòng 1: tên SP (cắt nếu dài)
            out += clip(item.name, width)
            // dòng 2: "  qty x unitPrice" trái, lineTotal phải
            val left = "  ${item.qty} x ${item.unitPrice}"
            out += leftRight(left, item.lineTotal, width)
        }
        out += "-".repeat(width)
        out += leftRight("TONG", data.total, width)
        out += leftRight("Khach dua", data.paid, width)
        out += leftRight("Thoi lai", data.change, width)
        data.footer?.let { out += "-".repeat(width); out += center(it, width) }
        return out
    }

    private fun clip(s: String, width: Int) = if (s.length <= width) s else s.substring(0, width)

    private fun center(s: String, width: Int): String {
        val c = clip(s, width)
        val pad = (width - c.length) / 2
        return (" ".repeat(pad) + c).let { it + " ".repeat(width - it.length) }
    }

    private fun leftRight(left: String, right: String, width: Int): String {
        val l = clip(left, width)
        val maxRight = width - l.length
        val r = if (right.length > maxRight) right.substring(0, maxRight.coerceAtLeast(0)) else right
        val gap = width - l.length - r.length
        return l + " ".repeat(gap.coerceAtLeast(0)) + r
    }
}
