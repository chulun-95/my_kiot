package com.mykiot.pos.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.auth.AuthRepository
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.LoginOutcome
import com.mykiot.pos.core.auth.TenantChoice
import com.mykiot.pos.core.network.ApiResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val phone: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val tenantChoices: List<TenantChoice> = emptyList(),
    val loggedInUser: CurrentUser? = null,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun onPhoneChange(v: String) = _state.update { it.copy(phone = v, errorMessage = null) }
    fun onPasswordChange(v: String) = _state.update { it.copy(password = v, errorMessage = null) }

    /** Submit with default tenant resolution. */
    fun submit() = doLogin(tenantId = null)

    /** Called after the user picks a shop from the tenant-selection list. */
    fun selectTenant(tenantId: Long) = doLogin(tenantId = tenantId)

    private fun doLogin(tenantId: Long?) {
        val s = _state.value
        if (s.phone.isBlank() || s.password.isBlank()) {
            _state.update { it.copy(errorMessage = "Vui lòng nhập số điện thoại và mật khẩu") }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null, tenantChoices = emptyList()) }
        viewModelScope.launch {
            when (val result = authRepository.login(s.phone.trim(), s.password, tenantId)) {
                is ApiResult.Success -> when (val outcome = result.data) {
                    is LoginOutcome.LoggedIn ->
                        _state.update { it.copy(loading = false, loggedInUser = outcome.user) }
                    is LoginOutcome.NeedsTenant ->
                        _state.update { it.copy(loading = false, tenantChoices = outcome.tenants) }
                }
                is ApiResult.Failure ->
                    _state.update { it.copy(loading = false, errorMessage = result.error.message) }
            }
        }
    }
}
