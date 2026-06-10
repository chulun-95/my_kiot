package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductSearchDto
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface ProductApi {
    @GET("products/search") suspend fun search(@Query("q") q: String): ProductSearchDto
    @GET("products/barcode/{code}") suspend fun byBarcode(@Path("code") code: String): ProductBriefDto
}
