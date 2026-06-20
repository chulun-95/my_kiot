package com.mykiot.pos.feature.receipt

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.GoodsReceiptDto
import com.mykiot.pos.feature.receipt.data.ReceiptRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class GoodsReceiptDetailUiState(
    val loading: Boolean = false,
    val completing: Boolean = false,
    val receipt: GoodsReceiptDto? = null,
    val error: ApiError? = null,
    val completedCode: String? = null,   // != null → đã hoàn tất, điều hướng quay lại
)

@HiltViewModel
class GoodsReceiptDetailViewModel @Inject constructor(
    private val repository: ReceiptRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(GoodsReceiptDetailUiState())
    val state: StateFlow<GoodsReceiptDetailUiState> = _state.asStateFlow()

    fun load(id: Long) {
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.getReceipt(id)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, receipt = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun complete() {
        val r = _state.value.receipt ?: return
        _state.update { it.copy(completing = true, error = null) }
        viewModelScope.launch {
            when (val res = repository.complete(r.id)) {
                is ApiResult.Success ->
                    _state.update { it.copy(completing = false, receipt = res.data, completedCode = res.data.code) }
                is ApiResult.Failure ->
                    _state.update { it.copy(completing = false, error = res.error) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(error = null) }
}
