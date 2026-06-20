package com.mykiot.pos.feature.receipt.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.InventoryApi
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.SupplierApi
import com.mykiot.pos.core.network.dto.GoodsReceiptBriefDto
import com.mykiot.pos.core.network.dto.GoodsReceiptCreateDto
import com.mykiot.pos.core.network.dto.GoodsReceiptDto
import com.mykiot.pos.core.network.dto.GoodsReceiptItemInputDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.feature.receipt.basket.ReceiptBasket
import com.mykiot.pos.feature.receipt.basket.ReceiptLine
import java.math.BigDecimal
import javax.inject.Inject

data class SupplierLite(val id: Long, val name: String)

open class ReceiptRepository @Inject constructor(
    private val productApi: ProductApi,
    private val supplierApi: SupplierApi,
    private val inventoryApi: InventoryApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun suppliers(search: String? = null): ApiResult<List<SupplierDto>> =
        runCatching { supplierApi.list(search).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun search(q: String): ApiResult<List<ProductBriefDto>> =
        runCatching { productApi.search(q).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun byBarcode(code: String): ApiResult<ProductBriefDto> =
        runCatching { productApi.byBarcode(code) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Tạo phiếu nhập DRAFT (chưa cộng tồn — hoàn tất ở màn chi tiết). */
    open suspend fun createDraft(
        basket: ReceiptBasket,
        supplierId: Long?,
        paidAmount: BigDecimal,
        paymentMethod: String,
        note: String?,
    ): ApiResult<GoodsReceiptDto> = runCatching {
        inventoryApi.createReceipt(
            GoodsReceiptCreateDto(
                supplierId = supplierId,
                paidAmount = paidAmount.toPlainString(),
                paymentMethod = paymentMethod,
                note = note?.ifBlank { null },
                items = basket.activeLines().map {
                    GoodsReceiptItemInputDto(
                        productId = it.productId,
                        unitId = it.unitId,
                        quantity = it.quantity.toPlainString(),
                        costPrice = it.costPrice.toPlainString(),
                    )
                },
            ),
        )
    }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Lấy chi tiết 1 phiếu nhập (màn chi tiết). */
    open suspend fun getReceipt(id: Long): ApiResult<GoodsReceiptDto> =
        runCatching { inventoryApi.getReceipt(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Hoàn tất phiếu nhập DRAFT → cộng tồn + tính giá vốn. */
    open suspend fun complete(id: Long): ApiResult<GoodsReceiptDto> =
        runCatching { inventoryApi.completeReceipt(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Danh sách phiếu nhập (phân trang). */
    open suspend fun listReceipts(page: Int = 1): ApiResult<PageResult<GoodsReceiptBriefDto>> =
        runCatching {
            val r = inventoryApi.listReceipts(page = page)
            PageResult.from(r.items, r.pagination)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Khi quét/chọn SP để nhập: giá vốn mặc định = costPrice hiện tại (nếu được xem), nếu null → 0. */
    open fun toReceiptLine(dto: ProductBriefDto): ReceiptLine = ReceiptLine(
        productId = dto.id,
        unitId = dto.matchedUnit?.id,
        name = dto.name,
        sku = dto.sku,
        unitName = dto.matchedUnit?.unitName ?: dto.unit,
        costPrice = BigDecimal((dto.costPrice ?: 0.0).toString()),
        quantity = BigDecimal.ONE,
    )
}
