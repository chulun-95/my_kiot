package com.mykiot.pos.core.ui

import com.mykiot.pos.core.network.ApiError
import org.junit.Assert.assertEquals
import org.junit.Test

class ErrorIconKindTest {
    @Test fun `network error maps to NETWORK`() =
        assertEquals(ErrorIconKind.NETWORK, errorIconKind(ApiError("NETWORK_ERROR", "Mất mạng", null)))

    @Test fun `401 maps to PERMISSION`() =
        assertEquals(ErrorIconKind.PERMISSION, errorIconKind(ApiError("X", "m", 401)))

    @Test fun `403 maps to PERMISSION`() =
        assertEquals(ErrorIconKind.PERMISSION, errorIconKind(ApiError("FORBIDDEN", "m", 403)))

    @Test fun `404 maps to NOT_FOUND`() =
        assertEquals(ErrorIconKind.NOT_FOUND, errorIconKind(ApiError("X", "m", 404)))

    @Test fun `400 maps to GENERIC`() =
        assertEquals(ErrorIconKind.GENERIC, errorIconKind(ApiError("VALIDATION", "m", 400)))

    @Test fun `500 maps to GENERIC`() =
        assertEquals(ErrorIconKind.GENERIC, errorIconKind(ApiError("X", "m", 500)))
}
