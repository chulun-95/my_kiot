package com.mykiot.pos.feature.report.data

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.ReportApi
import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
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
}
