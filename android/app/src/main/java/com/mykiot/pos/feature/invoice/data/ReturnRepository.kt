package com.mykiot.pos.feature.invoice.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ReturnApi
import com.mykiot.pos.core.network.dto.ReturnCreateDto
import com.mykiot.pos.core.network.dto.ReturnResultDto
import com.mykiot.pos.core.network.dto.ReturnableInvoiceDto
import javax.inject.Inject

open class ReturnRepository @Inject constructor(
    private val returnApi: ReturnApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun returnable(invoiceId: Long): ApiResult<ReturnableInvoiceDto> =
        runCatching { returnApi.returnable(invoiceId) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(body: ReturnCreateDto): ApiResult<ReturnResultDto> =
        runCatching { returnApi.create(body) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
