package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CategoryNodeDto(
    val id: Long,
    val name: String,
    @SerialName("parent_id") val parentId: Long? = null,
    val depth: Int = 1,
    val children: List<CategoryNodeDto> = emptyList(),
)

@Serializable
data class CategoryTreeDto(val items: List<CategoryNodeDto> = emptyList())

@Serializable
data class CategoryDto(
    val id: Long,
    val name: String,
    @SerialName("parent_id") val parentId: Long? = null,
    val depth: Int = 1,
)

@Serializable
data class CategoryCreateDto(
    val name: String,
    @SerialName("parent_id") val parentId: Long? = null,
)
