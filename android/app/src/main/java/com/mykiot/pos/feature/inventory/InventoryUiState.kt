package com.mykiot.pos.feature.inventory

import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.network.dto.StockMovementDto

/** Trạng thái dialog thẻ kho (kardex) của 1 sản phẩm. */
data class MovementsState(
    val item: InventoryItemDto? = null,
    val items: List<StockMovementDto> = emptyList(),
    val errorMessage: String? = null,
)
