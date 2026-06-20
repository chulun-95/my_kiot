package com.mykiot.pos.feature.inventory

import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
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
) : PagingListViewModel<InventoryItemDto>() {

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    private val _tab = MutableStateFlow(InventoryTab.ALL)
    val tab: StateFlow<InventoryTab> = _tab.asStateFlow()

    private val _lowStock = MutableStateFlow(LowStockState())
    val lowStock: StateFlow<LowStockState> = _lowStock.asStateFlow()

    /** Thẻ kho (movements) của 1 SP — tách khỏi state phân trang. */
    private val _movements = MutableStateFlow(MovementsState())
    val movements: StateFlow<MovementsState> = _movements.asStateFlow()

    fun load() = refresh()

    override suspend fun fetch(page: Int): ApiResult<PageResult<InventoryItemDto>> =
        repository.list(_query.value.takeIf { it.isNotBlank() }, page)

    fun onQueryChange(q: String) {
        _query.value = q
        if (q.isBlank() || q.length >= 2) refresh()
    }

    fun selectTab(tab: InventoryTab) {
        _tab.value = tab
        if (tab == InventoryTab.LOW && _lowStock.value.items.isEmpty()) loadLowStock()
    }

    fun loadLowStock() {
        _lowStock.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.lowStock()) {
                is ApiResult.Success -> _lowStock.update { it.copy(loading = false, items = r.data) }
                is ApiResult.Failure -> _lowStock.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun clearLowStockError() = _lowStock.update { it.copy(error = null) }

    fun openMovements(item: InventoryItemDto) {
        _movements.value = MovementsState(item = item)
        viewModelScope.launch {
            when (val r = repository.movements(item.productId)) {
                is ApiResult.Success -> _movements.update { it.copy(items = r.data) }
                is ApiResult.Failure -> _movements.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun closeMovements() = _movements.update { MovementsState() }
}
