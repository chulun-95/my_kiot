package com.mykiot.pos.feature.inventory

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.network.dto.StockMovementDto

enum class InventoryTab { ALL, LOW }

data class LowStockState(
    val items: List<InventoryItemDto> = emptyList(),
    val loading: Boolean = false,
    val error: ApiError? = null,
)

/** Trạng thái dialog thẻ kho (kardex) của 1 sản phẩm. */
data class MovementsState(
    val item: InventoryItemDto? = null,
    val items: List<StockMovementDto> = emptyList(),
    val errorMessage: String? = null,
)
