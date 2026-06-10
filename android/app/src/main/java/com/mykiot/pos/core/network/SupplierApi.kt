package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.SupplierListDto
import retrofit2.http.GET
import retrofit2.http.Query

interface SupplierApi {
    @GET("suppliers") suspend fun list(@Query("search") search: String? = null): SupplierListDto
}
