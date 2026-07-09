package com.mykiot.pos.core.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class MobileLoginRequest(
    val phone: String,
    val password: String,
    @SerialName("tenant_id") val tenantId: Long? = null,
)

@Serializable
data class RefreshRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class LogoutRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class ChangePasswordRequest(
    @SerialName("current_password") val currentPassword: String,
    @SerialName("new_password") val newPassword: String,
    @SerialName("confirm_password") val confirmPassword: String,
)

@Serializable
data class UserDto(
    val id: Long,
    @SerialName("full_name") val fullName: String,
    val phone: String? = null,
    val email: String? = null,
    val role: String,
)

@Serializable
data class TenantDto(
    val id: Long,
    val name: String,
    val slug: String,
    @SerialName("expires_at") val expiresAt: String? = null,
)

@Serializable
data class TenantOptionDto(
    val id: Long,
    val name: String,
    val role: String,
)

/**
 * /auth/mobile/login may return EITHER a success body OR a tenant-selection body
 * (when the phone exists in multiple shops and no tenant_id was provided).
 * Both shapes are optional-field unions parsed from the same JSON object.
 */
@Serializable
data class LoginResponseDto(
    // success fields
    val user: UserDto? = null,
    val tenant: TenantDto? = null,
    @SerialName("access_token") val accessToken: String? = null,
    @SerialName("refresh_token") val refreshToken: String? = null,
    // tenant-selection fields
    @SerialName("requires_tenant_selection") val requiresTenantSelection: Boolean = false,
    val tenants: List<TenantOptionDto>? = null,
)

@Serializable
data class TokenRefreshDto(
    val user: UserDto,
    val tenant: TenantDto,
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
)
