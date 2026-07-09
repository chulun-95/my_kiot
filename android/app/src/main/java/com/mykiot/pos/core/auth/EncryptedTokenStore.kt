package com.mykiot.pos.core.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class EncryptedTokenStore @Inject constructor(
    context: Context,
) : TokenStore {

    private val prefs: SharedPreferences = try {
        openEncryptedPrefs(context)
    } catch (_: Exception) {
        // File bị hỏng hoặc keystore không khớp → xóa và tạo lại (user cần login lại)
        context.deleteSharedPreferences(PREFS_NAME)
        openEncryptedPrefs(context)
    }

    private fun openEncryptedPrefs(context: Context): SharedPreferences {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        return EncryptedSharedPreferences.create(
            context,
            PREFS_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    override fun getAccessToken(): String? = prefs.getString(KEY_ACCESS, null)
    override fun getRefreshToken(): String? = prefs.getString(KEY_REFRESH, null)

    override fun save(accessToken: String, refreshToken: String) {
        prefs.edit().putString(KEY_ACCESS, accessToken).putString(KEY_REFRESH, refreshToken).apply()
    }

    override fun saveUser(user: CurrentUser) {
        prefs.edit().apply {
            putLong(KEY_USER_ID, user.id)
            putString(KEY_USER_NAME, user.fullName)
            putString(KEY_USER_ROLE, user.role)
            putLong(KEY_TENANT_ID, user.tenantId)
            putString(KEY_TENANT_NAME, user.tenantName)
            if (user.expiresAt != null) {
                putLong(KEY_TENANT_EXPIRES_AT, user.expiresAt.toEpochMilli())
            } else {
                remove(KEY_TENANT_EXPIRES_AT)
            }
        }.apply()
    }

    override fun getUser(): CurrentUser? {
        val role = prefs.getString(KEY_USER_ROLE, null) ?: return null
        return CurrentUser(
            id = prefs.getLong(KEY_USER_ID, 0L),
            fullName = prefs.getString(KEY_USER_NAME, "") ?: "",
            role = role,
            tenantId = prefs.getLong(KEY_TENANT_ID, 0L),
            tenantName = prefs.getString(KEY_TENANT_NAME, "") ?: "",
            expiresAt = if (prefs.contains(KEY_TENANT_EXPIRES_AT)) {
                Instant.ofEpochMilli(prefs.getLong(KEY_TENANT_EXPIRES_AT, 0L))
            } else {
                null
            },
        )
    }

    override fun clear() {
        prefs.edit().clear().apply()
    }

    override fun hasSession(): Boolean = getAccessToken() != null && getRefreshToken() != null

    private companion object {
        const val PREFS_NAME = "mykiot_secure_prefs"
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
        const val KEY_USER_ID = "user_id"
        const val KEY_USER_NAME = "user_name"
        const val KEY_USER_ROLE = "user_role"
        const val KEY_TENANT_ID = "tenant_id"
        const val KEY_TENANT_NAME = "tenant_name"
        const val KEY_TENANT_EXPIRES_AT = "tenant_expires_at"
    }
}
