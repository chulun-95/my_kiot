package com.mykiot.pos.core.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class EncryptedTokenStore @Inject constructor(
    context: Context,
) : TokenStore {

    private val prefs = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "mykiot_secure_prefs",
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
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
    }
}
