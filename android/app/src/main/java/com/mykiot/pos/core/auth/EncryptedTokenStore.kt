package com.mykiot.pos.core.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
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

    override fun clear() {
        prefs.edit().clear().apply()
    }

    override fun hasSession(): Boolean = getAccessToken() != null && getRefreshToken() != null

    private companion object {
        const val PREFS_NAME = "mykiot_secure_prefs"
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
    }
}
