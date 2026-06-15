package com.mykiot.pos.core.auth

import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.AuthApi
import com.mykiot.pos.core.network.ErrorMapper
import com.mykiot.pos.core.network.dto.ChangePasswordRequest
import com.mykiot.pos.core.network.dto.LoginResponseDto
import com.mykiot.pos.core.network.dto.LogoutRequest
import com.mykiot.pos.core.network.dto.MobileLoginRequest
import javax.inject.Inject
import javax.inject.Singleton

/** Outcome of a login attempt: either a session, or a tenant-selection prompt. */
sealed interface LoginOutcome {
    data class LoggedIn(val user: CurrentUser) : LoginOutcome
    data class NeedsTenant(val tenants: List<TenantChoice>) : LoginOutcome
}

data class TenantChoice(val id: Long, val name: String, val role: String)

@Singleton
class AuthRepository @Inject constructor(
    private val api: AuthApi,
    private val tokenStore: TokenStore,
    private val errorMapper: ErrorMapper,
) {
    fun hasSession(): Boolean = tokenStore.hasSession()

    suspend fun login(phone: String, password: String, tenantId: Long? = null): ApiResult<LoginOutcome> =
        try {
            val dto: LoginResponseDto = api.login(MobileLoginRequest(phone, password, tenantId))
            if (dto.requiresTenantSelection && dto.tenants != null) {
                ApiResult.Success(
                    LoginOutcome.NeedsTenant(
                        dto.tenants.map { TenantChoice(it.id, it.name, it.role) },
                    ),
                )
            } else if (dto.accessToken != null && dto.refreshToken != null &&
                dto.user != null && dto.tenant != null
            ) {
                tokenStore.save(dto.accessToken, dto.refreshToken)
                ApiResult.Success(
                    LoginOutcome.LoggedIn(
                        CurrentUser(
                            id = dto.user.id,
                            fullName = dto.user.fullName,
                            role = dto.user.role,
                            tenantId = dto.tenant.id,
                            tenantName = dto.tenant.name,
                        ),
                    ),
                )
            } else {
                ApiResult.Failure(ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại"))
            }
        } catch (t: Throwable) {
            ApiResult.Failure(errorMapper.map(t))
        }

    suspend fun logout() {
        val refresh = tokenStore.getRefreshToken()
        if (refresh != null) {
            runCatching { api.logout(LogoutRequest(refresh)) }
        }
        tokenStore.clear()
    }

    /** Đổi mật khẩu: backend thu hồi token cũ + cấp cặp mới → lưu lại để khỏi bị đăng xuất. */
    suspend fun changePassword(current: String, newPass: String, confirm: String): ApiResult<Unit> =
        try {
            val dto = api.changePassword(ChangePasswordRequest(current, newPass, confirm))
            tokenStore.save(dto.accessToken, dto.refreshToken)
            ApiResult.Success(Unit)
        } catch (t: Throwable) {
            ApiResult.Failure(errorMapper.map(t))
        }
}
