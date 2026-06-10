package com.mykiot.pos.core.network

import com.mykiot.pos.core.auth.TokenStore
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

/** Result of a successful token refresh. */
data class TokenPairResult(val accessToken: String, val refreshToken: String)

/** Performs the refresh network call; returns null on failure. */
fun interface RefreshCaller {
    fun refresh(refreshToken: String): TokenPairResult?
}

/**
 * On 401, refreshes the access token once (single-flight) and retries the request.
 * `refreshCallerProvider` is a provider to break the DI cycle (the refresh call uses
 * an OkHttp client that itself owns this authenticator).
 *
 * Provided via NetworkModule (not @Inject) to avoid a duplicate Hilt binding.
 */
class TokenAuthenticator(
    private val tokenStore: TokenStore,
    private val refreshCallerProvider: () -> RefreshCaller,
) : Authenticator {

    private val lock = Any()

    override fun authenticate(route: Route?, response: Response): Request? {
        // Give up if we've already retried once (avoid infinite loop).
        if (responseCount(response) >= 2) return null

        val currentRefresh = tokenStore.getRefreshToken() ?: return null
        val failedAccess = response.request.header("Authorization")

        synchronized(lock) {
            val latestAccess = tokenStore.getAccessToken()
            // Another thread already refreshed while we waited -> reuse new token.
            if (latestAccess != null && "Bearer $latestAccess" != failedAccess) {
                return response.request.newBuilder()
                    .header("Authorization", "Bearer $latestAccess")
                    .build()
            }

            val refreshed = refreshCallerProvider().refresh(currentRefresh)
            if (refreshed == null) {
                tokenStore.clear()
                return null
            }
            tokenStore.save(refreshed.accessToken, refreshed.refreshToken)
            return response.request.newBuilder()
                .header("Authorization", "Bearer ${refreshed.accessToken}")
                .build()
        }
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) { count++; prior = prior.priorResponse }
        return count
    }
}
