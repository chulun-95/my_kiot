package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.DashboardDto
import com.mykiot.pos.core.network.dto.EndOfDayDto
import com.mykiot.pos.core.network.dto.RevenueDto
import com.mykiot.pos.core.network.dto.TopProductsDto
import retrofit2.http.GET
import retrofit2.http.Query

interface ReportApi {
    @GET("reports/dashboard") suspend fun dashboard(): DashboardDto
    @GET("reports/end-of-day") suspend fun endOfDay(@Query("date") date: String? = null): EndOfDayDto

    @GET("reports/revenue")
    suspend fun revenue(
        @Query("from") from: String,
        @Query("to") to: String,
        @Query("group_by") groupBy: String = "day",
    ): RevenueDto

    @GET("reports/top-products")
    suspend fun topProducts(
        @Query("from") from: String? = null,
        @Query("to") to: String? = null,
        @Query("limit") limit: Int = 5,
    ): TopProductsDto
}
