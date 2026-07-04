package com.mykiot.pos.feature.report

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.util.last30DaysRange
import com.mykiot.pos.core.util.last7DaysRange
import com.mykiot.pos.core.util.thisMonthRange
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
        // Khoảng mặc định: 7 ngày gần nhất.
        if (_state.value.rangeFrom.isBlank()) {
            val (from, to) = last7DaysRange()
            _state.update { it.copy(rangeFrom = from, rangeTo = to) }
        }
        viewModelScope.launch {
            when (val r = repository.dashboard()) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, dashboard = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
            // Các nguồn OWNER-only: 403 (CASHIER) → bỏ qua, không báo lỗi.
            when (val e = repository.endOfDay()) {
                is ApiResult.Success -> _state.update { it.copy(eod = e.data) }
                is ApiResult.Failure -> _state.update { it.copy(eod = null) }
            }
            loadRevenue()
            when (val tp = repository.topProducts(5)) {
                is ApiResult.Success -> _state.update { it.copy(topProducts = tp.data) }
                is ApiResult.Failure -> _state.update { it.copy(topProducts = null) }
            }
        }
    }

    /** Đổi khoảng theo preset (7 / 30 ngày / tháng này) → tải lại doanh thu. */
    fun selectPreset(preset: RangePreset) {
        val range = when (preset) {
            RangePreset.LAST_7 -> last7DaysRange()
            RangePreset.LAST_30 -> last30DaysRange()
            RangePreset.THIS_MONTH -> thisMonthRange()
            RangePreset.CUSTOM -> return  // dùng setCustomRange
        }
        _state.update { it.copy(rangePreset = preset, rangeFrom = range.first, rangeTo = range.second) }
        loadRevenue()
    }

    /** Đổi khoảng tùy chọn từ DatePicker → tải lại doanh thu. */
    fun setCustomRange(from: String, to: String) {
        _state.update { it.copy(rangePreset = RangePreset.CUSTOM, rangeFrom = from, rangeTo = to) }
        loadRevenue()
    }

    /** Chọn 1 ngày trong dải để xem chi tiết. */
    fun selectDay(period: String?) = _state.update { it.copy(selectedPeriod = period) }

    private fun loadRevenue() {
        val from = _state.value.rangeFrom
        val to = _state.value.rangeTo
        if (from.isBlank() || to.isBlank()) return
        _state.update { it.copy(revenueLoading = true) }
        viewModelScope.launch {
            when (val rev = repository.revenueRange(from, to)) {
                is ApiResult.Success -> _state.update { st ->
                    val series = rev.data.series
                    // Giữ ngày đang chọn nếu còn trong dải, ngược lại chọn ngày gần nhất.
                    val keep = st.selectedPeriod?.takeIf { sp -> series.any { it.period == sp } }
                    st.copy(
                        revenueLoading = false,
                        revenue = rev.data,
                        selectedPeriod = keep ?: series.lastOrNull()?.period,
                    )
                }
                is ApiResult.Failure -> _state.update {
                    it.copy(revenueLoading = false, revenue = null, selectedPeriod = null)
                }
            }
        }
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }
}
