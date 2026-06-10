package com.mykiot.pos.core.network

import com.mykiot.pos.core.auth.TokenStore
import okhttp3.Interceptor
import okhttp3.Response

// Provided via NetworkModule (not @Inject) to avoid a duplicate Hilt binding.
class AuthInterceptor(
    private val tokenStore: TokenStore,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val builder = chain.request().newBuilder()
            .header("X-Requested-With", "XMLHttpRequest")
        tokenStore.getAccessToken()?.let { builder.header("Authorization", "Bearer $it") }
        return chain.proceed(builder.build())
    }
}
