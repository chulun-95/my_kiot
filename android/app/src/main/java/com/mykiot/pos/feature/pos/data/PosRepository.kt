package com.mykiot.pos.feature.pos.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CustomerApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.SalesApi
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceCompleteDto
import com.mykiot.pos.core.network.dto.InvoiceCreateDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceItemInputDto
import com.mykiot.pos.core.network.dto.PaymentInputDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.pos.cart.Cart
import com.mykiot.pos.feature.pos.cart.CartLine
import java.math.BigDecimal
import javax.inject.Inject

data class CustomerLite(val id: Long, val name: String, val phone: String?)

open class PosRepository @Inject constructor(
    private val productApi: ProductApi,
    private val customerApi: CustomerApi,
    private val salesApi: SalesApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun search(q: String): ApiResult<List<ProductBriefDto>> =
        runCatching { productApi.search(q).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun byBarcode(code: String): ApiResult<ProductBriefDto> =
        runCatching { productApi.byBarcode(code) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun findCustomerByPhone(phone: String): ApiResult<CustomerDto> =
        runCatching { customerApi.byPhone(phone) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    private fun buildCreateDto(cart: Cart, customerId: Long?) = InvoiceCreateDto(
        customerId = customerId,
        discountAmount = cart.invoiceDiscount.toPlainString(),
        items = cart.lines.map {
            InvoiceItemInputDto(
                productId = it.productId,
                unitId = it.unitId,
                quantity = it.quantity.toPlainString(),
                unitPrice = it.unitPrice.toPlainString(),
                discountAmount = it.discount.toPlainString(),
            )
        },
    )

    /**
     * Tạo hoá đơn DRAFT rồi complete trong 1 lần (POS bán nhanh).
     * Nếu [draftId] != null (đơn đang được khôi phục từ giỏ chờ) → update đúng draft đó rồi complete,
     * tránh tạo draft mồ côi.
     */
    open suspend fun checkout(
        cart: Cart,
        customerId: Long?,
        draftId: Long?,
        payments: List<PaymentInputDto>,
        allowDebt: Boolean,
    ): ApiResult<InvoiceDto> = runCatching {
        val dto = buildCreateDto(cart, customerId)
        val draft = if (draftId != null) salesApi.updateDraft(draftId, dto) else salesApi.create(dto)
        salesApi.complete(draft.id, InvoiceCompleteDto(payments = payments, allowDebt = allowDebt))
    }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Treo đơn: lưu giỏ hiện tại thành hoá đơn DRAFT (tạo mới hoặc cập nhật đơn đang sửa). */
    open suspend fun saveDraft(cart: Cart, customerId: Long?, draftId: Long?): ApiResult<InvoiceDto> =
        runCatching {
            val dto = buildCreateDto(cart, customerId)
            if (draftId != null) salesApi.updateDraft(draftId, dto) else salesApi.create(dto)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Danh sách hoá đơn đang treo (DRAFT). */
    open suspend fun drafts(): ApiResult<List<InvoiceBriefDto>> =
        runCatching { salesApi.drafts().items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Lấy chi tiết 1 đơn treo để khôi phục vào giỏ. */
    open suspend fun getInvoice(id: Long): ApiResult<InvoiceDto> =
        runCatching { salesApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    /** Map dòng hoá đơn (từ draft) → dòng giỏ hàng. */
    open fun toCartLine(item: com.mykiot.pos.core.network.dto.InvoiceItemDto): CartLine = CartLine(
        productId = item.productId,
        unitId = item.unitId,
        name = item.productName,
        sku = item.productSku,
        unitName = item.unit ?: "",
        unitPrice = BigDecimal(item.unitPrice),
        quantity = BigDecimal(item.quantity),
        discount = BigDecimal(item.discountAmount),
    )

    open fun toCartLine(dto: ProductBriefDto): CartLine {
        val mu = dto.matchedUnit
        return if (mu != null) {
            CartLine(
                productId = dto.id, unitId = mu.id, name = dto.name, sku = dto.sku,
                unitName = mu.unitName,
                unitPrice = BigDecimal((mu.salePrice ?: dto.salePrice * mu.conversionRate).toString()),
                quantity = BigDecimal.ONE,
            )
        } else {
            CartLine(
                productId = dto.id, unitId = null, name = dto.name, sku = dto.sku,
                unitName = dto.unit, unitPrice = BigDecimal(dto.salePrice.toString()),
                quantity = BigDecimal.ONE,
            )
        }
    }
}
