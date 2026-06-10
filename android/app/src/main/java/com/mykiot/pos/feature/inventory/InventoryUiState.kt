package com.mykiot.pos.feature.inventory

import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.network.dto.StockMovementDto

data class InventoryUiState(
    val items: List<InventoryItemDto> = emptyList(),
    val query: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val movementsFor: InventoryItemDto? = null,
    val movements: List<StockMovementDto> = emptyList(),
)
