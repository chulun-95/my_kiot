package com.mykiot.pos.core.network

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
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
        is SerializationException -> ApiError("PARSE_ERROR", "Dữ liệu phản hồi không hợp lệ")
        else -> ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại")
    }

    private fun mapHttp(ex: HttpException): ApiError {
        val status = ex.code()
        val raw = runCatching { ex.response()?.errorBody()?.string() }.getOrNull()
        val root = raw
            ?.let { runCatching { json.parseToJsonElement(it) }.getOrNull() }
            ?.let { it as? JsonObject }

        // 1) Định dạng chuẩn của backend: { "error": { "code", "message", "details" } }
        (root?.get("error") as? JsonObject)?.let { err ->
            val code = err["code"]?.jsonPrimitive?.contentOrNull?.ifBlank { null }
            val message = err["message"]?.jsonPrimitive?.contentOrNull?.ifBlank { null }
            if (message != null) return ApiError(code ?: "UNKNOWN", message, status)
        }

        // 2) Định dạng FastAPI/Pydantic: { "detail": "..." } hoặc { "detail": [ { "msg": ... } ] }
        root?.get("detail")?.let { detail ->
            detailMessage(detail)?.let { return ApiError("VALIDATION", it, status) }
        }

        return ApiError("UNKNOWN", "Có lỗi xảy ra, vui lòng thử lại", status)
    }

    private fun detailMessage(detail: JsonElement): String? = when (detail) {
        is JsonPrimitive -> detail.contentOrNull?.ifBlank { null }
        is JsonArray -> detail.firstOrNull()
            ?.let { (it as? JsonObject)?.get("msg")?.jsonPrimitive?.contentOrNull }
            ?.ifBlank { null }
        else -> null
    }
}
