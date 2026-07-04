package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.CancelInvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceCompleteDto
import com.mykiot.pos.core.network.dto.InvoiceCreateDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceDraftListDto
import com.mykiot.pos.core.network.dto.InvoiceListDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface SalesApi {
    @POST("invoices") suspend fun create(@Body body: InvoiceCreateDto): InvoiceDto
    @PUT("invoices/{id}") suspend fun updateDraft(@Path("id") id: Long, @Body body: InvoiceCreateDto): InvoiceDto
    @GET("invoices/{id}") suspend fun get(@Path("id") id: Long): InvoiceDto
    @POST("invoices/{id}/complete") suspend fun complete(@Path("id") id: Long, @Body body: InvoiceCompleteDto): InvoiceDto
    @GET("invoices/drafts") suspend fun drafts(): InvoiceDraftListDto

    @GET("invoices")
    suspend fun list(
        @Query("status") status: String? = null,
        @Query("search") search: String? = null,
        @Query("from") from: String? = null,
        @Query("to") to: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
    ): InvoiceListDto

    @POST("invoices/{id}/cancel")
    suspend fun cancel(@Path("id") id: Long, @Body body: CancelInvoiceDto): InvoiceDto
}
