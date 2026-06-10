package com.mykiot.pos.feature.report

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.feature.report.data.ReportRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ReportViewModel @Inject constructor(
    private val repository: ReportRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ReportUiState())
    val state: StateFlow<ReportUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.dashboard()) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, dashboard = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
            // EOD chỉ dành cho OWNER; nếu CASHIER bị 403 → bỏ qua, không báo lỗi.
            when (val e = repository.endOfDay()) {
                is ApiResult.Success -> _state.update { it.copy(eod = e.data) }
                is ApiResult.Failure -> _state.update { it.copy(eod = null) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
