package com.mykiot.pos.feature.report

import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto

/** Khoảng thời gian xem doanh thu. */
enum class RangePreset { LAST_7, LAST_30, THIS_MONTH, CUSTOM }

data class ReportUiState(
    val dashboard: DashboardDto? = null,
    val eod: EndOfDayDto? = null,            // null nếu CASHIER (403) hoặc chưa tải
    val revenue: RevenueDto? = null,         // null nếu CASHIER (403)
    val topProducts: TopProductsDto? = null, // null nếu CASHIER (403)
    val rangePreset: RangePreset = RangePreset.LAST_7,
    val rangeFrom: String = "",              // "YYYY-MM-DD"
    val rangeTo: String = "",                // "YYYY-MM-DD"
    val selectedPeriod: String? = null,      // ngày đang chọn để xem chi tiết
    val revenueLoading: Boolean = false,
    val loading: Boolean = false,
    val errorMessage: String? = null,
)
