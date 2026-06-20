package com.mykiot.pos.feature.customer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerCreateDto
import com.mykiot.pos.core.network.dto.CustomerResponseDto
import com.mykiot.pos.feature.customer.data.CustomerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AddCustomerUiState(
    val name: String = "",
    val phone: String = "",
    val email: String = "",
    val address: String = "",
    val note: String = "",
    val saving: Boolean = false,
    val created: CustomerResponseDto? = null,
    val errorMessage: String? = null,
)

@HiltViewModel
class AddCustomerViewModel @Inject constructor(
    private val repository: CustomerRepository,
    private val res: ResProvider,
) : ViewModel() {
    private val _state = MutableStateFlow(AddCustomerUiState())
    val state: StateFlow<AddCustomerUiState> = _state.asStateFlow()

    fun onName(v: String) = _state.update { it.copy(name = v) }
    fun onPhone(v: String) = _state.update { it.copy(phone = v) }
    fun onEmail(v: String) = _state.update { it.copy(email = v) }
    fun onAddress(v: String) = _state.update { it.copy(address = v) }
    fun onNote(v: String) = _state.update { it.copy(note = v) }
    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun submit() {
        val s = _state.value
        if (s.name.isBlank()) {
            _state.update { it.copy(errorMessage = res.get(R.string.cat_customer_err_name_required)) }
            return
        }
        val phone = s.phone.trim()
        if (phone.isBlank()) {
            _state.update { it.copy(errorMessage = res.get(R.string.cat_customer_err_phone_required)) }
            return
        }
        if (!Regex("^0[35789]\\d{8}$").matches(phone)) {
            _state.update { it.copy(errorMessage = res.get(R.string.cat_customer_err_phone_invalid)) }
            return
        }
        _state.update { it.copy(saving = true, errorMessage = null) }
        viewModelScope.launch {
            val body = CustomerCreateDto(
                name = s.name.trim(),
                phone = s.phone.trim(),
                email = s.email.trim().ifBlank { null },
                address = s.address.trim().ifBlank { null },
                note = s.note.trim().ifBlank { null },
            )
            when (val r = repository.create(body)) {
                is ApiResult.Success -> _state.update { it.copy(saving = false, created = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(saving = false, errorMessage = r.error.message) }
            }
        }
    }
}
