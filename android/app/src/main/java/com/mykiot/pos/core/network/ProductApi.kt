package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.core.network.dto.ProductListDto
import com.mykiot.pos.core.network.dto.ProductSearchDto
import com.mykiot.pos.core.network.dto.ProductUpdateDto
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface ProductApi {
    @GET("products")
    suspend fun list(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): ProductListDto

    @GET("products/{id}") suspend fun get(@Path("id") id: Long): ProductBriefDto
    @GET("products/search") suspend fun search(@Query("q") q: String): ProductSearchDto
    @GET("products/barcode/{code}") suspend fun byBarcode(@Path("code") code: String): ProductBriefDto

    @POST("products") suspend fun create(@Body body: ProductCreateDto): ProductBriefDto
    @PUT("products/{id}") suspend fun update(@Path("id") id: Long, @Body body: ProductUpdateDto): ProductBriefDto
    @DELETE("products/{id}") suspend fun delete(@Path("id") id: Long)
}
