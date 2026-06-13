package com.mykiot.pos.feature.report.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ReportApi
import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto
import com.mykiot.pos.core.util.last7DaysRange
import javax.inject.Inject

open class ReportRepository @Inject constructor(
    private val reportApi: ReportApi,
    private val errorMapper: ErrorMapper,
) {
    open suspend fun dashboard(): ApiResult<DashboardDto> =
        runCatching { reportApi.dashboard() }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun endOfDay(): ApiResult<EndOfDayDto> =
        runCatching { reportApi.endOfDay() }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })

    open suspend fun revenueLast7Days(): ApiResult<RevenueDto> {
        val (from, to) = last7DaysRange()
        return runCatching { reportApi.revenue(from = from, to = to, groupBy = "day") }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
    }

    open suspend fun topProducts(limit: Int = 5): ApiResult<TopProductsDto> =
        runCatching { reportApi.topProducts(limit = limit) }
            .fold({ ApiResult.Success(it) }, { ApiResult.Failure(errorMapper.map(it)) })
}
