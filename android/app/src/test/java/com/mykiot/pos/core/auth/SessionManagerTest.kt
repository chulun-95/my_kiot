package com.mykiot.pos.core.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionManagerTest {
    private val owner = CurrentUser(1, "Chủ", "OWNER", 1, "Shop")
    private val cashier = CurrentUser(2, "Thu ngân", "CASHIER", 1, "Shop")

    @Test
    fun `set updates current and isOwner`() {
        val sm = SessionManager(FakeTokenStore())
        sm.set(owner)
        assertEquals(owner, sm.current.value)
        assertTrue(sm.isOwner)
    }

    @Test
    fun `restore reads persisted user from store`() {
        val store = FakeTokenStore().apply { saveUser(cashier) }
        val sm = SessionManager(store)
        sm.restore()
        assertEquals(cashier, sm.current.value)
        assertFalse(sm.isOwner)
    }

    @Test
    fun `clear empties current`() {
        val sm = SessionManager(FakeTokenStore())
        sm.set(owner)
        sm.clear()
        assertNull(sm.current.value)
        assertFalse(sm.isOwner)
    }
}
