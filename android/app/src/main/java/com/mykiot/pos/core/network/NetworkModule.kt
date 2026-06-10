package com.mykiot.pos.core.network

import com.mykiot.pos.BuildConfig
import com.mykiot.pos.core.auth.TokenStore
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides @Singleton
    fun json(): Json = Json { ignoreUnknownKeys = true }

    @Provides @Singleton
    fun authInterceptor(tokenStore: TokenStore) = AuthInterceptor(tokenStore)

    /**
     * A bare client used ONLY for the refresh call, so the refresh request itself
     * cannot trigger the TokenAuthenticator (no infinite 401 loop).
     */
    @Provides @Singleton @RefreshClient
    fun refreshRetrofit(json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(OkHttpClient.Builder().build())
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides @Singleton
    fun refreshCallerProvider(@RefreshClient retrofit: Retrofit): () -> RefreshCaller {
        val api = retrofit.create(AuthApi::class.java)
        return {
            RefreshCaller { refreshToken ->
                runCatching {
                    kotlinx.coroutines.runBlocking {
                        val dto = api.refresh(com.mykiot.pos.core.network.dto.RefreshRequest(refreshToken))
                        TokenPairResult(dto.accessToken, dto.refreshToken)
                    }
                }.getOrNull()
            }
        }
    }

    @Provides @Singleton
    fun tokenAuthenticator(tokenStore: TokenStore, provider: () -> RefreshCaller) =
        TokenAuthenticator(tokenStore, provider)

    @Provides @Singleton
    fun okHttpClient(
        authInterceptor: AuthInterceptor,
        authenticator: TokenAuthenticator,
    ): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
            else HttpLoggingInterceptor.Level.NONE
        }
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .authenticator(authenticator)
            .build()
    }

    @Provides @Singleton
    fun retrofit(client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides @Singleton
    fun authApi(retrofit: Retrofit): AuthApi = retrofit.create(AuthApi::class.java)

    @Provides @Singleton
    fun productApi(retrofit: Retrofit): ProductApi = retrofit.create(ProductApi::class.java)

    @Provides @Singleton
    fun customerApi(retrofit: Retrofit): CustomerApi = retrofit.create(CustomerApi::class.java)

    @Provides @Singleton
    fun salesApi(retrofit: Retrofit): SalesApi = retrofit.create(SalesApi::class.java)

    @Provides @Singleton
    fun supplierApi(retrofit: Retrofit): SupplierApi = retrofit.create(SupplierApi::class.java)

    @Provides @Singleton
    fun inventoryApi(retrofit: Retrofit): InventoryApi = retrofit.create(InventoryApi::class.java)

    @Provides @Singleton
    fun reportApi(retrofit: Retrofit): ReportApi = retrofit.create(ReportApi::class.java)
}
