package com.mykiot.pos.feature.report

import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto

data class ReportUiState(
    val dashboard: DashboardDto? = null,
    val eod: EndOfDayDto? = null,        // null nếu CASHIER (không có quyền) hoặc chưa tải
    val loading: Boolean = false,
    val errorMessage: String? = null,
)
