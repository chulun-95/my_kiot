package com.mykiot.pos.core.auth

interface TokenStore {
    fun getAccessToken(): String?
    fun getRefreshToken(): String?
    fun save(accessToken: String, refreshToken: String)
    fun clear()
    fun hasSession(): Boolean
}
