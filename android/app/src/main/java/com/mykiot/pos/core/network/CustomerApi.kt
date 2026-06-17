package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerDetailDto
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.core.network.dto.CustomerListDto
import com.mykiot.pos.core.network.dto.CustomerResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface CustomerApi {
    @GET("customers")
    suspend fun list(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): CustomerListDto
    @GET("customers/phone/{phone}") suspend fun byPhone(@Path("phone") phone: String): CustomerDto
    @GET("customers/{id}") suspend fun get(@Path("id") id: Long): CustomerDetailDto
    @POST("customers") suspend fun create(@Body body: CustomerCreateDto): CustomerResponseDto
}
