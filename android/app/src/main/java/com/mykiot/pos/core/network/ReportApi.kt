package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
import retrofit2.http.GET
import retrofit2.http.Query

interface ReportApi {
    @GET("reports/dashboard") suspend fun dashboard(): DashboardDto
    @GET("reports/end-of-day") suspend fun endOfDay(@Query("date") date: String? = null): EndOfDayDto
}
