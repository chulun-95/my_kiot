package com.mykiot.pos.feature.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.feature.product.data.ProductRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import javax.inject.Inject

data class AddProductUiState(
    val name: String = "",
    val barcode: String = "",
    val sku: String = "",
    val unit: String = "cái",
    val costPrice: String = "",
    val salePrice: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val created: ProductBriefDto? = null,
)

@HiltViewModel
class AddProductViewModel @Inject constructor(
    private val repository: ProductRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(AddProductUiState())
    val state: StateFlow<AddProductUiState> = _state.asStateFlow()

    private var prefilled = false

    fun prefillBarcode(barcode: String) {
        if (prefilled) return
        prefilled = true
        if (barcode.isNotBlank()) _state.update { it.copy(barcode = barcode) }
    }

    fun onName(v: String) = _state.update { it.copy(name = v) }
    fun onBarcode(v: String) = _state.update { it.copy(barcode = v) }
    fun onSku(v: String) = _state.update { it.copy(sku = v) }
    fun onUnit(v: String) = _state.update { it.copy(unit = v) }
    fun onCost(v: String) = _state.update { it.copy(costPrice = v) }
    fun onSale(v: String) = _state.update { it.copy(salePrice = v) }
    fun clearError() = _state.update { it.copy(errorMessage = null) }

    private fun normalizePrice(v: String): String? {
        val t = v.trim().replace(",", "")
        if (t.isBlank()) return "0"
        return try { BigDecimal(t); t } catch (_: Exception) { null }
    }

    fun submit() {
        val s = _state.value
        if (s.name.isBlank()) {
            _state.update { it.copy(errorMessage = "Vui lòng nhập tên sản phẩm") }
            return
        }
        val cost = normalizePrice(s.costPrice)
        val sale = normalizePrice(s.salePrice)
        if (cost == null || sale == null) {
            _state.update { it.copy(errorMessage = "Giá nhập / giá bán không hợp lệ") }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            val dto = ProductCreateDto(
                name = s.name.trim(),
                sku = s.sku.trim().ifBlank { null },
                barcode = s.barcode.trim().ifBlank { null },
                unit = s.unit.trim().ifBlank { "cái" },
                costPrice = cost,
                salePrice = sale,
            )
            when (val r = repository.create(dto)) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, created = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }
}
