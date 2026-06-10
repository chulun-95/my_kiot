package com.mykiot.pos.core.auth

class FakeTokenStore : TokenStore {
    private var access: String? = null
    private var refresh: String? = null

    override fun getAccessToken(): String? = access
    override fun getRefreshToken(): String? = refresh
    override fun save(accessToken: String, refreshToken: String) {
        access = accessToken; refresh = refreshToken
    }
    override fun clear() { access = null; refresh = null }
    override fun hasSession(): Boolean = access != null && refresh != null
}
