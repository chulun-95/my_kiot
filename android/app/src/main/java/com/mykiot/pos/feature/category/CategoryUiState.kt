package com.mykiot.pos.feature.category

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.dto.CategoryNodeDto

data class CategoryUiState(
    val nodes: List<CategoryNodeDto> = emptyList(),
    val loading: Boolean = false,
    val error: ApiError? = null,
    val editorOpen: Boolean = false,
    val editorParentId: Long? = null,
    val editorEditingId: Long? = null,
    val editorName: String = "",
)
