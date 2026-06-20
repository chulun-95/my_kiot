package com.mykiot.pos.feature.account

import com.mykiot.pos.R
import com.mykiot.pos.core.auth.AuthRepository
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.ApiResult
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ChangePasswordViewModelTest {
    private val repo = mockk<AuthRepository>(relaxed = true)
    private val res = FakeResProvider()

    @Before fun setUp() = Dispatchers.setMain(StandardTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `short new password sets error, no api call`() = runTest {
        val vm = ChangePasswordViewModel(repo, res)
        vm.onCurrent("oldpass")
        vm.onNew("123")
        vm.onConfirm("123")
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(R.string.misc_change_password_min_length), vm.state.value.errorMessage)
        coVerify(exactly = 0) { repo.changePassword(any(), any(), any()) }
    }

    @Test
    fun `mismatch confirm sets error`() = runTest {
        val vm = ChangePasswordViewModel(repo, res)
        vm.onCurrent("oldpass")
        vm.onNew("abcdef")
        vm.onConfirm("abcxyz")
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertEquals(res.get(R.string.misc_change_password_mismatch), vm.state.value.errorMessage)
    }

    @Test
    fun `valid submit calls repo and sets done`() = runTest {
        coEvery { repo.changePassword("oldpass", "abcdef", "abcdef") } returns ApiResult.Success(Unit)
        val vm = ChangePasswordViewModel(repo, res)
        vm.onCurrent("oldpass")
        vm.onNew("abcdef")
        vm.onConfirm("abcdef")
        vm.submit()
        testScheduler.advanceUntilIdle()
        assertTrue(vm.state.value.done)
        coVerify { repo.changePassword("oldpass", "abcdef", "abcdef") }
    }
}
