package com.mykiot.pos.core.network

import com.mykiot.pos.core.auth.FakeTokenStore
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class TokenAuthenticatorTest {

    private lateinit var server: MockWebServer

    @Before fun setUp() { server = MockWebServer().apply { start() } }
    @After fun tearDown() { server.shutdown() }

    private fun clientWith(store: FakeTokenStore): OkHttpClient {
        val refreshApiProvider = { RefreshCaller { refreshToken ->
            // call the mock server's /auth/mobile/refresh directly (no DI here)
            val resp = OkHttpClient().newCall(
                Request.Builder()
                    .url(server.url("auth/mobile/refresh"))
                    .post(okhttp3.RequestBody.create(null, ByteArray(0)))
                    .header("X-Refresh", refreshToken)
                    .build(),
            ).execute()
            val newAccess = resp.header("X-New-Access")
            val newRefresh = resp.header("X-New-Refresh")
            val success = resp.isSuccessful
            resp.close()
            if (success && newAccess != null && newRefresh != null) {
                TokenPairResult(newAccess, newRefresh)
            } else null
        } }
        return OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor(store))
            .authenticator(TokenAuthenticator(store, refreshApiProvider))
            .build()
    }

    @Test
    fun `on 401 it refreshes once and retries with new token`() {
        val store = FakeTokenStore().apply { save("old-access", "old-refresh") }

        // 1) protected call -> 401
        server.enqueue(MockResponse().setResponseCode(401))
        // 2) refresh call -> 200 with new tokens
        server.enqueue(MockResponse().setResponseCode(200)
            .addHeader("X-New-Access", "new-access")
            .addHeader("X-New-Refresh", "new-refresh"))
        // 3) retried protected call -> 200
        server.enqueue(MockResponse().setResponseCode(200).setBody("ok"))

        val client = clientWith(store)
        val resp = client.newCall(
            Request.Builder().url(server.url("products")).build(),
        ).execute()

        assertEquals(200, resp.code)
        assertEquals("ok", resp.body?.string())
        resp.close()

        // store updated with rotated tokens
        assertEquals("new-access", store.getAccessToken())
        assertEquals("new-refresh", store.getRefreshToken())

        // first request used old token
        val first = server.takeRequest()
        assertEquals("Bearer old-access", first.getHeader("Authorization"))
        // refresh request carried the old refresh token
        val refresh = server.takeRequest()
        assertEquals("old-refresh", refresh.getHeader("X-Refresh"))
        // retried request used new token
        val retried = server.takeRequest()
        assertEquals("Bearer new-access", retried.getHeader("Authorization"))
    }

    @Test
    fun `when refresh fails it clears session and gives up`() {
        val store = FakeTokenStore().apply { save("old-access", "old-refresh") }
        server.enqueue(MockResponse().setResponseCode(401)) // protected -> 401
        server.enqueue(MockResponse().setResponseCode(401)) // refresh -> 401

        val client = clientWith(store)
        val resp = client.newCall(
            Request.Builder().url(server.url("products")).build(),
        ).execute()

        // OkHttp returns the last 401 once the authenticator returns null
        assertEquals(401, resp.code)
        resp.close()
        assertTrue(!store.hasSession())
    }
}
