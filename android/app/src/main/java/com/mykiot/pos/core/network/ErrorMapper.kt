package com.mykiot.pos.core.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ErrorMapper @Inject constructor() {

    private val json = Json { ignoreUnknownKeys = true }

    fun map(throwable: Throwable): ApiError = when (throwable) {
        is HttpException -> mapHttp(throwable)
        is IOException -> ApiError("NETWORK_ERROR", "Mất kết nối mạng, vui lòng thử lại")
        else -> ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại")
    }

    private fun mapHttp(ex: HttpException): ApiError {
        val status = ex.code()
        val raw = runCatching { ex.response()?.errorBody()?.string() }.getOrNull()
        val parsed = raw?.let { runCatching { json.decodeFromString<ErrorEnvelope>(it) }.getOrNull() }
        val body = parsed?.error
        return if (body != null && body.message.isNotBlank()) {
            ApiError(body.code.ifBlank { "UNKNOWN" }, body.message, status)
        } else {
            ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại", status)
        }
    }

    @Serializable
    private data class ErrorEnvelope(val error: ErrorBody? = null)

    @Serializable
    private data class ErrorBody(
        val code: String = "",
        val message: String = "",
        @SerialName("details") val details: Map<String, String>? = null,
    )
}
