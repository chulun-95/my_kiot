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

    @Test
    fun `saveUser then getUser returns same user`() {
        val store = FakeTokenStore()
        val user = CurrentUser(id = 7, fullName = "Chị Tư", role = "OWNER", tenantId = 3, tenantName = "Tạp hóa Tư")
        store.saveUser(user)
        assertEquals(user, store.getUser())
    }

    @Test
    fun `clear removes saved user`() {
        val store = FakeTokenStore()
        store.saveUser(CurrentUser(1, "A", "CASHIER", 1, "Shop"))
        store.clear()
        assertNull(store.getUser())
    }
}
