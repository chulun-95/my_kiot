package com.mykiot.pos.feature.receipt

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.R
import com.mykiot.pos.core.hardware.Beeper
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.feature.receipt.data.ReceiptDraftCache
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
    private val draftCache: ReceiptDraftCache,
    private val res: ResProvider,
) : ViewModel() {

    private val _state = MutableStateFlow(ReceiptUiState())
    val state: StateFlow<ReceiptUiState> = _state.asStateFlow()

    init {
        // Khôi phục phiếu nhập đang dở (nếu lần trước thoát mà chưa hoàn tất).
        draftCache.load()?.let { snap ->
            _state.update { it.copy(basket = snap.basket, supplier = snap.supplier) }
        }
    }

    /** Lưu giỏ hiện tại xuống cache (gọi sau mỗi thay đổi giỏ/NCC). */
    private fun persist() {
        val s = _state.value
        draftCache.save(s.basket, s.supplier)
    }

    fun loadSuppliers() {
        viewModelScope.launch {
            when (val r = repository.suppliers()) {
                is ApiResult.Success -> _state.update { it.copy(suppliers = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun setSupplier(s: SupplierLite?) {
        _state.update { it.copy(supplier = s) }
        persist()
    }

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
                is ApiResult.Success -> {
                    Beeper.pip()  // quét + thêm thành công → "pip"
                    addToBasket(r.data)
                }
                is ApiResult.Failure -> {
                    Beeper.error()  // không tìm thấy / lỗi → "tit tit"
                    // 404 = chưa có SP với mã này → hỏi tạo SP mới; lỗi khác → báo lỗi
                    if (r.error.httpStatus == 404) {
                        _state.update { it.copy(unknownBarcode = code) }
                    } else {
                        _state.update { it.copy(errorMessage = r.error.message) }
                    }
                }
            }
        }
    }

    // ---- Luồng thêm NCC mới ----
    fun requestAddSupplier() = _state.update { it.copy(showAddSupplier = true) }
    fun dismissAddSupplier() = _state.update { it.copy(showAddSupplier = false) }
    fun onSupplierCreated(s: SupplierLite) {
        _state.update { it.copy(supplier = s, showAddSupplier = false) }
        persist()
    }

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
        persist()
    }

    fun setQuantity(index: Int, qty: BigDecimal) {
        _state.update { it.copy(basket = it.basket.setQuantity(index, qty)) }
        persist()
    }

    fun setCost(index: Int, cost: BigDecimal) {
        _state.update { it.copy(basket = it.basket.setCost(index, cost)) }
        persist()
    }

    fun removeLine(index: Int) {
        _state.update { it.copy(basket = it.basket.removeLine(index)) }
        persist()  // giỏ rỗng → cache tự xoá (xem ReceiptDraftCache.save)
    }

    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun consumeReceiptCode() = _state.update { it.copy(lastReceiptCode = null) }

    fun consumeDraftId() = _state.update { it.copy(lastDraftId = null) }

    // ----- Thanh toán -----
    fun setPayFull(v: Boolean) = _state.update { it.copy(payFull = v) }
    fun setPaidAmount(v: Long) = _state.update { it.copy(paidAmount = v.coerceAtLeast(0)) }
    fun setPaymentMethod(m: String) = _state.update { it.copy(paymentMethod = m) }
    fun setNote(n: String) = _state.update { it.copy(note = n) }

    /** Tiền trả thực tế = tổng nếu "trả đủ", ngược lại = số đã nhập. */
    private fun effectivePaid(s: ReceiptUiState): BigDecimal =
        if (s.payFull) s.basket.total() else BigDecimal(s.paidAmount)

    /** Lưu phiếu nhập DRAFT rồi điều hướng sang màn chi tiết để hoàn tất. */
    fun saveDraft() {
        val s = _state.value
        if (!s.basket.hasItems()) {
            _state.update { it.copy(errorMessage = res.get(R.string.receipt_error_no_items)) }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            val r = repository.createDraft(
                s.basket, s.supplier?.id, effectivePaid(s), s.paymentMethod, s.note,
            )
            when (r) {
                is ApiResult.Success -> {
                    draftCache.clear()  // đã lưu lên server → xoá cache phiếu nhập dở
                    _state.update {
                        it.copy(
                            loading = false, basket = it.basket.clear(), supplier = null,
                            payFull = true, paidAmount = 0, paymentMethod = "CASH", note = "",
                            lastDraftId = r.data.id,
                        )
                    }
                }
                is ApiResult.Failure ->
                    _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }
}
