package com.mykiot.pos.core.network

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException

class ErrorMapperTest {

    private val mapper = ErrorMapper()

    private fun httpException(status: Int, body: String): HttpException {
        val response = Response.error<Any>(
            status,
            body.toResponseBody("application/json".toMediaType()),
        )
        return HttpException(response)
    }

    @Test
    fun `parses backend error body and prefers its vietnamese message`() {
        val ex = httpException(
            401,
            """{"error":{"code":"INVALID_CREDENTIALS","message":"Sai số điện thoại hoặc mật khẩu"}}""",
        )
        val err = mapper.map(ex)
        assertEquals("INVALID_CREDENTIALS", err.code)
        assertEquals("Sai số điện thoại hoặc mật khẩu", err.message)
        assertEquals(401, err.httpStatus)
    }

    @Test
    fun `network IOException maps to connection message`() {
        val err = mapper.map(IOException("timeout"))
        assertEquals("NETWORK_ERROR", err.code)
        assertEquals("Mất kết nối mạng, vui lòng thử lại", err.message)
    }

    @Test
    fun `unparseable error body falls back to generic vietnamese message`() {
        val ex = httpException(500, "<html>boom</html>")
        val err = mapper.map(ex)
        assertEquals("UNKNOWN", err.code)
        assertEquals("Có lỗi xảy ra, vui lòng thử lại", err.message)
        assertEquals(500, err.httpStatus)
    }
}
