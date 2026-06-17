package com.mykiot.pos.feature.receipt.data

import android.content.Context
import com.mykiot.pos.feature.receipt.basket.ReceiptBasket
import com.mykiot.pos.feature.receipt.basket.ReceiptLine
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.math.BigDecimal
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
private data class CachedLine(
    val productId: Long,
    val unitId: Long?,
    val name: String,
    val sku: String,
    val unitName: String,
    val costPrice: String,
    val quantity: String,
)

@Serializable
private data class CachedReceipt(
    val supplierId: Long? = null,
    val supplierName: String? = null,
    val lines: List<CachedLine> = emptyList(),
)

/** Snapshot phiếu nhập đang dở để khôi phục khi mở lại màn (sống qua cả khởi động lại app). */
data class ReceiptDraftSnapshot(
    val basket: ReceiptBasket,
    val supplier: SupplierLite?,
)

/**
 * Lưu/khôi phục phiếu nhập chưa hoàn tất vào SharedPreferences.
 * Chỉ xoá khi: hoàn tất nhập, hoặc user xoá hết sản phẩm trong giỏ.
 */
@Singleton
class ReceiptDraftCache @Inject constructor(
    @ApplicationContext context: Context,
) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val json = Json { ignoreUnknownKeys = true }

    fun load(): ReceiptDraftSnapshot? {
        val raw = prefs.getString(KEY, null) ?: return null
        val cached = try { json.decodeFromString<CachedReceipt>(raw) } catch (_: Exception) { return null }
        if (cached.lines.isEmpty()) return null
        val lines = cached.lines.map {
            ReceiptLine(
                productId = it.productId,
                unitId = it.unitId,
                name = it.name,
                sku = it.sku,
                unitName = it.unitName,
                costPrice = it.costPrice.toBigDecimalOrZero(),
                quantity = it.quantity.toBigDecimalOrZero(),
            )
        }
        val supplier = cached.supplierId?.let { SupplierLite(it, cached.supplierName ?: "") }
        return ReceiptDraftSnapshot(ReceiptBasket(lines), supplier)
    }

    /** Lưu giỏ hiện tại; nếu giỏ rỗng thì xoá cache luôn. */
    fun save(basket: ReceiptBasket, supplier: SupplierLite?) {
        if (basket.isEmpty()) { clear(); return }
        val cached = CachedReceipt(
            supplierId = supplier?.id,
            supplierName = supplier?.name,
            lines = basket.lines.map {
                CachedLine(
                    productId = it.productId,
                    unitId = it.unitId,
                    name = it.name,
                    sku = it.sku,
                    unitName = it.unitName,
                    costPrice = it.costPrice.toPlainString(),
                    quantity = it.quantity.toPlainString(),
                )
            },
        )
        prefs.edit().putString(KEY, json.encodeToString(cached)).apply()
    }

    fun clear() {
        prefs.edit().remove(KEY).apply()
    }

    private fun String.toBigDecimalOrZero(): BigDecimal =
        try { BigDecimal(this) } catch (_: Exception) { BigDecimal.ZERO }

    private companion object {
        const val PREFS = "mykiot_receipt_draft"
        const val KEY = "draft"
    }
}
