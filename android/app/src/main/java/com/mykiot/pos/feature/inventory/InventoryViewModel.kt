package com.mykiot.pos.feature.inventory

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.feature.inventory.data.InventoryRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class InventoryViewModel @Inject constructor(
    private val repository: InventoryRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(InventoryUiState())
    val state: StateFlow<InventoryUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.list(_state.value.query.takeIf { it.isNotBlank() })) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, items = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun onQueryChange(q: String) {
        _state.update { it.copy(query = q) }
        if (q.isBlank() || q.length >= 2) load()
    }

    fun openMovements(item: InventoryItemDto) {
        _state.update { it.copy(movementsFor = item, movements = emptyList()) }
        viewModelScope.launch {
            when (val r = repository.movements(item.productId)) {
                is ApiResult.Success -> _state.update { it.copy(movements = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun closeMovements() = _state.update { it.copy(movementsFor = null, movements = emptyList()) }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
