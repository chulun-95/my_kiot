package com.mykiot.pos.feature.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.product.data.ProductListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProductDetailUiState(
    val product: ProductBriefDto? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val deleteError: ApiError? = null,
    val isOwner: Boolean = false,
    val deleted: Boolean = false,
)

@HiltViewModel
class ProductDetailViewModel @Inject constructor(
    private val repository: ProductListRepository,
    sessionManager: SessionManager,
) : ViewModel() {
    private val _state = MutableStateFlow(ProductDetailUiState(isOwner = sessionManager.isOwner))
    val state: StateFlow<ProductDetailUiState> = _state.asStateFlow()

    fun load(id: Long) {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.get(id)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, product = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun delete(id: Long) {
        _state.update { it.copy(loading = true, deleteError = null) }
        viewModelScope.launch {
            when (val r = repository.delete(id)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, deleted = true) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, deleteError = r.error) }
            }
        }
    }

    fun clearDeleteError() = _state.update { it.copy(deleteError = null) }
}
