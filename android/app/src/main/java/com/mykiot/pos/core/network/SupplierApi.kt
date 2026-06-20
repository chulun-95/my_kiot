package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.SupplierCreateDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.network.dto.SupplierListDto
import com.mykiot.pos.core.network.dto.SupplierResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface SupplierApi {
    @GET("suppliers") suspend fun list(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): SupplierListDto

    @GET("suppliers/{id}") suspend fun getById(@Path("id") id: Long): SupplierResponseDto

    /** Tạo NCC mới. */
    @POST("suppliers") suspend fun create(@Body body: SupplierCreateDto): SupplierDto

    @PUT("suppliers/{id}") suspend fun update(
        @Path("id") id: Long,
        @Body body: SupplierCreateDto,
    ): SupplierResponseDto
}
