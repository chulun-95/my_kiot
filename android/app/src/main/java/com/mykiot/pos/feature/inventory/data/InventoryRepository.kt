package com.mykiot.pos.feature.inventory.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.InventoryApi
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.network.dto.StockMovementDto
import com.mykiot.pos.core.ui.paging.PageResult
import javax.inject.Inject

open class InventoryRepository @Inject constructor(
    private val inventoryApi: InventoryApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun list(search: String?, page: Int = 1): ApiResult<PageResult<InventoryItemDto>> =
        runCatching {
            val r = inventoryApi.inventory(search = search, page = page)
            PageResult.from(r.items, r.pagination)
        }.fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun lowStock(): ApiResult<List<InventoryItemDto>> =
        runCatching { inventoryApi.lowStock().items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun movements(productId: Long): ApiResult<List<StockMovementDto>> =
        runCatching { inventoryApi.movements(productId).items }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
