package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.dto.CustomerDto

data class CustomerListUiState(
    val query: String = "",
    val items: List<CustomerDto> = emptyList(),
    val loading: Boolean = false,
    val errorMessage: String? = null,
)
