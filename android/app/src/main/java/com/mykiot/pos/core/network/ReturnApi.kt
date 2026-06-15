package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.ReturnCreateDto
import com.mykiot.pos.core.network.dto.ReturnResultDto
import com.mykiot.pos.core.network.dto.ReturnableInvoiceDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ReturnApi {
    @GET("returns/returnable/{invoiceId}")
    suspend fun returnable(@Path("invoiceId") invoiceId: Long): ReturnableInvoiceDto

    @POST("returns")
    suspend fun create(@Body body: ReturnCreateDto): ReturnResultDto
}
