package com.mykiot.pos.core.auth

class FakeTokenStore : TokenStore {
    private var access: String? = null
    private var refresh: String? = null
    private var user: CurrentUser? = null

    override fun getAccessToken(): String? = access
    override fun getRefreshToken(): String? = refresh
    override fun save(accessToken: String, refreshToken: String) {
        access = accessToken; refresh = refreshToken
    }
    override fun saveUser(user: CurrentUser) { this.user = user }
    override fun getUser(): CurrentUser? = user
    override fun clear() { access = null; refresh = null; user = null }
    override fun hasSession(): Boolean = access != null && refresh != null
}
