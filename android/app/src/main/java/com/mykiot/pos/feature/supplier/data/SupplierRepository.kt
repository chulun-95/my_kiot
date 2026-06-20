package com.mykiot.pos.feature.supplier.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.SupplierApi
import com.mykiot.pos.core.network.dto.SupplierCreateDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.network.dto.SupplierResponseDto
import com.mykiot.pos.core.ui.paging.PageResult
import javax.inject.Inject

open class SupplierRepository @Inject constructor(
    private val supplierApi: SupplierApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?, page: Int = 1): ApiResult<PageResult<SupplierDto>> =
        runCatching {
            val r = supplierApi.list(search = search, page = page)
            PageResult.from(r.items, r.pagination)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun getById(id: Long): ApiResult<SupplierResponseDto> =
        runCatching { supplierApi.getById(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(dto: SupplierCreateDto): ApiResult<SupplierDto> =
        runCatching { supplierApi.create(dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun update(id: Long, dto: SupplierCreateDto): ApiResult<SupplierResponseDto> =
        runCatching { supplierApi.update(id, dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
