package com.mykiot.pos.navigation

import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.FakeTokenStore
import com.mykiot.pos.core.auth.SessionManager
import org.junit.Assert.assertEquals
import org.junit.Test

class HubViewModelTest {
    @Test
    fun `exposes current user from session`() {
        val sm = SessionManager(FakeTokenStore())
        sm.set(CurrentUser(1, "Chủ", "OWNER", 1, "Shop"))
        val vm = HubViewModel(sm)
        assertEquals("OWNER", vm.user.value?.role)
    }
}
