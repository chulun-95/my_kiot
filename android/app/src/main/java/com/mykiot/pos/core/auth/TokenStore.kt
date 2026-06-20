package com.mykiot.pos.core.auth

interface TokenStore {
    fun getAccessToken(): String?
    fun getRefreshToken(): String?
    fun save(accessToken: String, refreshToken: String)
    fun saveUser(user: CurrentUser)
    fun getUser(): CurrentUser?
    fun clear()
    fun hasSession(): Boolean
}
