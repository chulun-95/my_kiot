package com.mykiot.pos.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.HubSummaryDto
import com.mykiot.pos.feature.report.data.ReportRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HubUiState(
    val captions: Map<String, String> = emptyMap(),
)

private val HUB_CAPTION_ROUTES: List<String> = hubGroups.flatMap { it.items }.map { it.route }

@HiltViewModel
class HubViewModel @Inject constructor(
    sessionManager: SessionManager,
    private val reportRepository: ReportRepository,
    private val res: ResProvider,
) : ViewModel() {
    val user: StateFlow<CurrentUser?> = sessionManager.current

    private val _state = MutableStateFlow(HubUiState(captions = buildCaptions(null)))
    val state: StateFlow<HubUiState> = _state.asStateFlow()

    /** Tải số liệu tổng hợp cho Hub; lỗi thì giữ nguyên caption tĩnh (không báo lỗi). */
    fun load() {
        viewModelScope.launch {
            val summary = when (val r = reportRepository.hubSummary()) {
                is ApiResult.Success -> r.data
                is ApiResult.Failure -> null
            }
            _state.update { it.copy(captions = buildCaptions(summary)) }
        }
    }

    private fun buildCaptions(summary: HubSummaryDto?): Map<String, String> =
        HUB_CAPTION_ROUTES.associateWith { route -> captionFor(route, summary, res) }
}
