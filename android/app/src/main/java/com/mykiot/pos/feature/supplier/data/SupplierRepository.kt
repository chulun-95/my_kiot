package com.mykiot.pos.feature.supplier.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.SupplierApi
import com.mykiot.pos.core.network.dto.SupplierCreateDto
import com.mykiot.pos.core.network.dto.SupplierDto
import javax.inject.Inject

open class SupplierRepository @Inject constructor(
    private val supplierApi: SupplierApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun create(dto: SupplierCreateDto): ApiResult<SupplierDto> =
        runCatching { supplierApi.create(dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
