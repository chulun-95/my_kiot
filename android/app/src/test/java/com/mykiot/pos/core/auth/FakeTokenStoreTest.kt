package com.mykiot.pos.core.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class FakeTokenStoreTest {

    @Test
    fun `save then read returns tokens and hasSession true`() {
        val store = FakeTokenStore()
        assertFalse(store.hasSession())
        store.save("acc", "ref")
        assertEquals("acc", store.getAccessToken())
        assertEquals("ref", store.getRefreshToken())
        assertTrue(store.hasSession())
    }

    @Test
    fun `clear wipes tokens`() {
        val store = FakeTokenStore()
        store.save("acc", "ref")
        store.clear()
        assertNull(store.getAccessToken())
        assertNull(store.getRefreshToken())
        assertFalse(store.hasSession())
    }
}
