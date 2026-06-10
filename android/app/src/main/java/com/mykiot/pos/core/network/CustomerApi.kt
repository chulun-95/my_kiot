package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.core.network.dto.CustomerListDto
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface CustomerApi {
    @GET("customers") suspend fun list(@Query("search") search: String? = null): CustomerListDto
    @GET("customers/phone/{phone}") suspend fun byPhone(@Path("phone") phone: String): CustomerDto
}
