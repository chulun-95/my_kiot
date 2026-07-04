package com.mykiot.pos.feature.product.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.core.network.dto.ProductUpdateDto
import javax.inject.Inject

open class ProductRepository @Inject constructor(
    private val productApi: ProductApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun get(id: Long): ApiResult<ProductBriefDto> =
        runCatching { productApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(dto: ProductCreateDto): ApiResult<ProductBriefDto> =
        runCatching { productApi.create(dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun update(id: Long, dto: ProductUpdateDto): ApiResult<ProductBriefDto> =
        runCatching { productApi.update(id, dto) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
