package com.mykiot.pos.feature.auth

import com.mykiot.pos.core.auth.AuthRepository
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.LoginOutcome
import com.mykiot.pos.core.auth.TenantChoice
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LoginViewModelTest {

    private val repo: AuthRepository = mockk(relaxed = true)

    // Unconfined: the login coroutine runs eagerly so state.value is final after submit().
    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun user() = CurrentUser(1, "Owner", "OWNER", 10, "Shop")

    @Test
    fun `successful login sets loggedInUser and clears loading`() = runTest {
        coEvery { repo.login("0901234567", "secret123", null) } returns
            ApiResult.Success(LoginOutcome.LoggedIn(user()))
        val vm = LoginViewModel(repo)

        vm.onPhoneChange("0901234567")
        vm.onPasswordChange("secret123")
        vm.submit()

        val s = vm.state.value
        assertEquals(false, s.loading)
        assertNull(s.errorMessage)
        assertNotNull(s.loggedInUser)
        assertEquals("OWNER", s.loggedInUser?.role)
    }

    @Test
    fun `invalid credentials surfaces vietnamese error`() = runTest {
        coEvery { repo.login(any(), any(), null) } returns
            ApiResult.Failure(ApiError("INVALID_CREDENTIALS", "Sai số điện thoại hoặc mật khẩu", 401))
        val vm = LoginViewModel(repo)
        vm.onPhoneChange("0901234567"); vm.onPasswordChange("nope")

        vm.submit()

        val s = vm.state.value
        assertEquals(false, s.loading)
        assertNull(s.loggedInUser)
        assertEquals("Sai số điện thoại hoặc mật khẩu", s.errorMessage)
    }

    @Test
    fun `multi-tenant login surfaces tenant choices`() = runTest {
        coEvery { repo.login(any(), any(), null) } returns
            ApiResult.Success(
                LoginOutcome.NeedsTenant(
                    listOf(TenantChoice(1, "Shop A", "OWNER"), TenantChoice(2, "Shop B", "CASHIER")),
                ),
            )
        val vm = LoginViewModel(repo)
        vm.onPhoneChange("0901234567"); vm.onPasswordChange("secret123")

        vm.submit()

        val s = vm.state.value
        assertEquals(false, s.loading)
        assertEquals(2, s.tenantChoices.size)
        assertEquals("Shop A", s.tenantChoices.first().name)
    }

    @Test
    fun `blank fields produce validation error without calling repo`() = runTest {
        val vm = LoginViewModel(repo)

        vm.submit()

        assertEquals("Vui lòng nhập số điện thoại và mật khẩu", vm.state.value.errorMessage)
        coVerify(exactly = 0) { repo.login(any(), any(), any()) }
    }
}
