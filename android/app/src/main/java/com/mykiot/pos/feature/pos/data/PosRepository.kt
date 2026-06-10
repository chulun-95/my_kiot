package com.mykiot.pos.feature.pos.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CustomerApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.SalesApi
import com.mykiot.pos.core.network.dto.CustomerDto
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

    /** Tạo hoá đơn DRAFT rồi complete trong 1 lần (POS bán nhanh). */
    open suspend fun checkout(
        cart: Cart,
        customerId: Long?,
        payments: List<PaymentInputDto>,
        allowDebt: Boolean,
    ): ApiResult<InvoiceDto> = runCatching {
        val draft = salesApi.create(
            InvoiceCreateDto(
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
            ),
        )
        salesApi.complete(draft.id, InvoiceCompleteDto(payments = payments, allowDebt = allowDebt))
    }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

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
