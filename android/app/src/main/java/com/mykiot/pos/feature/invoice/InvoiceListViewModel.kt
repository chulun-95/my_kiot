package com.mykiot.pos.feature.invoice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
open class InvoiceListViewModel @Inject constructor(
    private val repository: InvoiceListRepository,
) : ViewModel() {

    protected open val loadStatus: String? = null

    private val _state = MutableStateFlow(InvoiceListUiState())
    val state: StateFlow<InvoiceListUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.list(status = loadStatus)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, items = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }

    fun setFilter(f: InvoiceFilter) = _state.update { it.copy(filter = f) }

    fun requestCancel(id: Long) = _state.update { it.copy(cancelingId = id) }

    fun dismissCancel() = _state.update { it.copy(cancelingId = null) }

    fun cancelInvoice(id: Long, reason: String) {
        _state.update { it.copy(cancelingId = null) }
        viewModelScope.launch {
            when (val r = repository.cancel(id, reason)) {
                is ApiResult.Success -> _state.update { s ->
                    s.copy(items = s.items.map { if (it.id == id) it.copy(status = "CANCELLED") else it })
                }
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
