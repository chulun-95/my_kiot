package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.InvoiceCompleteDto
import com.mykiot.pos.core.network.dto.InvoiceCreateDto
import com.mykiot.pos.core.network.dto.InvoiceDto
import com.mykiot.pos.core.network.dto.InvoiceDraftListDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface SalesApi {
    @POST("invoices") suspend fun create(@Body body: InvoiceCreateDto): InvoiceDto
    @GET("invoices/{id}") suspend fun get(@Path("id") id: Long): InvoiceDto
    @POST("invoices/{id}/complete") suspend fun complete(@Path("id") id: Long, @Body body: InvoiceCompleteDto): InvoiceDto
    @GET("invoices/drafts") suspend fun drafts(): InvoiceDraftListDto
}
