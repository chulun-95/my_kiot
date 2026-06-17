package com.mykiot.pos.feature.invoice.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.SalesApi
import com.mykiot.pos.core.network.dto.CancelInvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.ui.paging.PageResult
import javax.inject.Inject

open class InvoiceListRepository @Inject constructor(
    private val salesApi: SalesApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(status: String?, page: Int = 1): ApiResult<PageResult<InvoiceBriefDto>> =
        runCatching {
            val r = salesApi.list(status = status, page = page)
            PageResult.from(r.items, r.pagination)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun cancel(id: Long, reason: String): ApiResult<InvoiceDto> =
        runCatching { salesApi.cancel(id, CancelInvoiceDto(reason)) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
