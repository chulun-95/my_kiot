package com.mykiot.pos.feature.supplier

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.SupplierCreateDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.feature.supplier.data.SupplierRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AddSupplierUiState(
    val name: String = "",
    val phone: String = "",
    val address: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val created: SupplierDto? = null,
)

@HiltViewModel
class AddSupplierViewModel @Inject constructor(
    private val repository: SupplierRepository,
    private val res: ResProvider,
) : ViewModel() {

    private val _state = MutableStateFlow(AddSupplierUiState())
    val state: StateFlow<AddSupplierUiState> = _state.asStateFlow()

    private var prefilled = false

    /** Đổ tên ban đầu (vd từ ô tìm kiếm) — chỉ chạy 1 lần. */
    fun prefillName(name: String) {
        if (prefilled) return
        prefilled = true
        if (name.isNotBlank()) _state.update { it.copy(name = name) }
    }

    fun onName(v: String) = _state.update { it.copy(name = v) }
    fun onPhone(v: String) = _state.update { it.copy(phone = v) }
    fun onAddress(v: String) = _state.update { it.copy(address = v) }
    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun submit() {
        val s = _state.value
        if (s.name.isBlank()) {
            _state.update { it.copy(errorMessage = res.get(R.string.cat_supplier_err_name_required)) }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            val dto = SupplierCreateDto(
                name = s.name.trim(),
                phone = s.phone.trim().ifBlank { null },
                address = s.address.trim().ifBlank { null },
            )
            when (val r = repository.create(dto)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, created = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }
}
