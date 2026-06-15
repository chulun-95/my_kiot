package com.mykiot.pos.core.network

import com.mykiot.pos.core.network.dto.ChangePasswordRequest
import com.mykiot.pos.core.network.dto.LoginResponseDto
import com.mykiot.pos.core.network.dto.LogoutRequest
import com.mykiot.pos.core.network.dto.MobileLoginRequest
import com.mykiot.pos.core.network.dto.RefreshRequest
import com.mykiot.pos.core.network.dto.TokenRefreshDto
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.PUT

interface AuthApi {

    @POST("auth/mobile/login")
    suspend fun login(@Body body: MobileLoginRequest): LoginResponseDto

    @POST("auth/mobile/refresh")
    suspend fun refresh(@Body body: RefreshRequest): TokenRefreshDto

    @POST("auth/mobile/logout")
    suspend fun logout(@Body body: LogoutRequest)

    @PUT("auth/mobile/change-password")
    suspend fun changePassword(@Body body: ChangePasswordRequest): TokenRefreshDto
}
