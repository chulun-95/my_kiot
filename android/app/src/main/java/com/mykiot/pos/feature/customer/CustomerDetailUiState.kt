package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.dto.CustomerDetailDto

data class CustomerDetailUiState(
    val customer: CustomerDetailDto? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
)
