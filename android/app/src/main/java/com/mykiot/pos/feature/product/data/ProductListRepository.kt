package com.mykiot.pos.feature.product.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ProductApi
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
import javax.inject.Inject

open class ProductListRepository @Inject constructor(
    private val productApi: ProductApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?, page: Int = 1): ApiResult<PageResult<ProductBriefDto>> =
        runCatching {
            val r = productApi.list(search = search.takeIf { !it.isNullOrBlank() }, page = page)
            PageResult.from(r.items, r.pagination)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun get(id: Long): ApiResult<ProductBriefDto> =
        runCatching { productApi.get(id) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun delete(id: Long): ApiResult<Unit> =
        runCatching { productApi.delete(id) }
            .fold({ ApiResult.Success(Unit) }, { ApiResult.Failure(errorMapper.map(it)) })
}
