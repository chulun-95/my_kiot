package com.mykiot.pos.feature.customer.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CustomerApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.core.network.dto.CustomerResponseDto
import javax.inject.Inject

open class CustomerRepository @Inject constructor(
    private val customerApi: CustomerApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?): ApiResult<List<CustomerDto>> =
        runCatching { customerApi.list(search = search).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun get(id: Long): ApiResult<CustomerDetailDto> =
        runCatching { customerApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(body: CustomerCreateDto): ApiResult<CustomerResponseDto> =
        runCatching { customerApi.create(body) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
