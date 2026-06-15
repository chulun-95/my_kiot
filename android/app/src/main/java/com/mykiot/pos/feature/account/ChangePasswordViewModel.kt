package com.mykiot.pos.feature.account

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.auth.AuthRepository
import com.mykiot.pos.core.network.ApiResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChangePasswordUiState(
    val current: String = "",
    val newPass: String = "",
    val confirm: String = "",
    val saving: Boolean = false,
    val done: Boolean = false,
    val errorMessage: String? = null,
)

@HiltViewModel
class ChangePasswordViewModel @Inject constructor(
    private val repository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ChangePasswordUiState())
    val state: StateFlow<ChangePasswordUiState> = _state.asStateFlow()

    fun onCurrent(v: String) = _state.update { it.copy(current = v) }
    fun onNew(v: String) = _state.update { it.copy(newPass = v) }
    fun onConfirm(v: String) = _state.update { it.copy(confirm = v) }
    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun submit() {
        val s = _state.value
        when {
            s.current.isBlank() ->
                { _state.update { it.copy(errorMessage = "Vui lòng nhập mật khẩu hiện tại") }; return }
            s.newPass.length < 6 ->
                { _state.update { it.copy(errorMessage = "Mật khẩu mới phải có ít nhất 6 ký tự") }; return }
            s.newPass != s.confirm ->
                { _state.update { it.copy(errorMessage = "Xác nhận mật khẩu không khớp") }; return }
        }
        _state.update { it.copy(saving = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.changePassword(s.current, s.newPass, s.confirm)) {
                is ApiResult.Success -> _state.update { it.copy(saving = false, done = true) }
                is ApiResult.Failure -> _state.update { it.copy(saving = false, errorMessage = r.error.message) }
            }
        }
    }
}
