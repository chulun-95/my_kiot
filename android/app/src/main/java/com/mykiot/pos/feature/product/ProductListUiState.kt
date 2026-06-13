package com.mykiot.pos.feature.product

import com.mykiot.pos.core.network.dto.ProductBriefDto

data class ProductListUiState(
    val loading: Boolean = false,
    val items: List<ProductBriefDto> = emptyList(),
    val query: String = "",
    val errorMessage: String? = null,
)
