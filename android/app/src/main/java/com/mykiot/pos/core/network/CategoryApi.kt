package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.core.network.dto.CategoryDto
import com.mykiot.pos.core.network.dto.CategoryTreeDto
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path

interface CategoryApi {
    @GET("categories") suspend fun tree(): CategoryTreeDto
    @POST("categories") suspend fun create(@Body body: CategoryCreateDto): CategoryDto
    @PUT("categories/{id}") suspend fun update(@Path("id") id: Long, @Body body: CategoryCreateDto): CategoryDto
    @DELETE("categories/{id}") suspend fun delete(@Path("id") id: Long)
}
