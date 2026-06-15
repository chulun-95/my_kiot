package com.mykiot.pos.feature.receipt

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.receipt.data.ReceiptRepository
import com.mykiot.pos.feature.receipt.data.SupplierLite
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import javax.inject.Inject

@HiltViewModel
class ReceiptViewModel @Inject constructor(
    private val repository: ReceiptRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ReceiptUiState())
    val state: StateFlow<ReceiptUiState> = _state.asStateFlow()

    fun loadSuppliers() {
        viewModelScope.launch {
            when (val r = repository.suppliers()) {
                is ApiResult.Success -> _state.update { it.copy(suppliers = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun setSupplier(s: SupplierLite?) = _state.update { it.copy(supplier = s) }

    fun onQueryChange(q: String) {
        _state.update { it.copy(query = q) }
        if (q.length >= 2) {
            viewModelScope.launch {
                when (val r = repository.search(q)) {
                    is ApiResult.Success -> _state.update { it.copy(searchResults = r.data) }
                    is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
                }
            }
        } else {
            _state.update { it.copy(searchResults = emptyList()) }
        }
    }

    fun onBarcodeScanned(code: String) {
        viewModelScope.launch {
            when (val r = repository.byBarcode(code)) {
                is ApiResult.Success -> addToBasket(r.data)
                is ApiResult.Failure ->
                    // 404 = chưa có SP với mã này → hỏi tạo SP mới; lỗi khác → báo lỗi
                    if (r.error.httpStatus == 404) {
                        _state.update { it.copy(unknownBarcode = code) }
                    } else {
                        _state.update { it.copy(errorMessage = r.error.message) }
                    }
            }
        }
    }

    // ---- Luồng thêm NCC mới ----
    fun requestAddSupplier() = _state.update { it.copy(showAddSupplier = true) }
    fun dismissAddSupplier() = _state.update { it.copy(showAddSupplier = false) }
    fun onSupplierCreated(s: SupplierLite) =
        _state.update { it.copy(supplier = s, showAddSupplier = false) }

    // ---- Luồng quét mã lạ → thêm SP mới ----
    fun confirmAddUnknownProduct() =
        _state.update { it.copy(addProductBarcode = it.unknownBarcode ?: "", unknownBarcode = null) }
    fun dismissUnknownBarcode() = _state.update { it.copy(unknownBarcode = null) }
    fun cancelAddProduct() = _state.update { it.copy(addProductBarcode = null) }
    fun onProductCreated(dto: ProductBriefDto) {
        _state.update { it.copy(addProductBarcode = null) }
        addToBasket(dto)
    }

    fun addFromSearch(dto: ProductBriefDto) = addToBasket(dto)

    private fun addToBasket(dto: ProductBriefDto) {
        val line = repository.toReceiptLine(dto)
        _state.update {
            it.copy(
                basket = it.basket.addScanned(line),
                errorMessage = null, query = "", searchResults = emptyList(),
            )
        }
    }

    fun setQuantity(index: Int, qty: BigDecimal) =
        _state.update { it.copy(basket = it.basket.setQuantity(index, qty)) }

    fun setCost(index: Int, cost: BigDecimal) =
        _state.update { it.copy(basket = it.basket.setCost(index, cost)) }

    fun removeLine(index: Int) =
        _state.update { it.copy(basket = it.basket.removeLine(index)) }

    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun consumeReceiptCode() = _state.update { it.copy(lastReceiptCode = null) }

    fun submit(paidAmount: BigDecimal, paymentMethod: String) {
        val s = _state.value
        if (s.basket.isEmpty()) {
            _state.update { it.copy(errorMessage = "Phiếu nhập trống") }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.submit(s.basket, s.supplier?.id, paidAmount, paymentMethod)) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        loading = false, basket = it.basket.clear(),
                        supplier = null, lastReceiptCode = r.data.code,
                    )
                }
                is ApiResult.Failure ->
                    _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }
}
