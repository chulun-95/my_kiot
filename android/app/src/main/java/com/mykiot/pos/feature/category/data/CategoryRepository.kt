package com.mykiot.pos.feature.category.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.CategoryApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.core.network.dto.CategoryDto
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import javax.inject.Inject

open class CategoryRepository @Inject constructor(
    private val categoryApi: CategoryApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun tree(): ApiResult<List<CategoryNodeDto>> =
        runCatching { categoryApi.tree().items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun create(body: CategoryCreateDto): ApiResult<CategoryDto> =
        runCatching { categoryApi.create(body) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun update(id: Long, body: CategoryCreateDto): ApiResult<CategoryDto> =
        runCatching { categoryApi.update(id, body) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun delete(id: Long): ApiResult<Unit> =
        runCatching { categoryApi.delete(id) }
            .fold({ ApiResult.Success(Unit) }, { ApiResult.Failure(errorMapper.map(it)) })
}
