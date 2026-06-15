package com.mykiot.pos.feature.product.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.dto.ProductBriefDto
import javax.inject.Inject

open class ProductListRepository @Inject constructor(
    private val productApi: ProductApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?): ApiResult<List<ProductBriefDto>> =
        runCatching { productApi.list(search = search.takeIf { !it.isNullOrBlank() }).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun get(id: Long): ApiResult<ProductBriefDto> =
        runCatching { productApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
