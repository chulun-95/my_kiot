package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.GoodsReceiptCreateDto
import com.mykiot.pos.core.network.dto.GoodsReceiptDto
import com.mykiot.pos.core.network.dto.GoodsReceiptListDto
import com.mykiot.pos.core.network.dto.InventoryListDto
import com.mykiot.pos.core.network.dto.LowStockDto
import com.mykiot.pos.core.network.dto.StockMovementsDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface InventoryApi {
    // ---- goods receipts (Phase 3) ----
    @POST("goods-receipts")
    suspend fun createReceipt(@Body body: GoodsReceiptCreateDto): GoodsReceiptDto

    @GET("goods-receipts/{id}")
    suspend fun getReceipt(@Path("id") id: Long): GoodsReceiptDto

    @POST("goods-receipts/{id}/complete")
    suspend fun completeReceipt(@Path("id") id: Long): GoodsReceiptDto

    @GET("goods-receipts")
    suspend fun listReceipts(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
    ): GoodsReceiptListDto

    // ---- inventory (Phase 4) ----
    @GET("inventory")
    suspend fun inventory(
        @Query("search") search: String? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20,
    ): InventoryListDto

    @GET("inventory/low-stock")
    suspend fun lowStock(): LowStockDto

    @GET("inventory/{productId}/movements")
    suspend fun movements(@Path("productId") productId: Long): StockMovementsDto
}
