package com.mykiot.pos.feature.invoice

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ReturnCreateDto
import com.mykiot.pos.core.network.dto.ReturnItemInputDto
import com.mykiot.pos.core.network.dto.ReturnResultDto
import com.mykiot.pos.feature.invoice.data.ReturnRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import javax.inject.Inject

data class ReturnLineUi(
    val invoiceItemId: Long,
    val name: String,
    val sku: String,
    val unit: String?,
    val returnableQty: BigDecimal,
    val unitPrice: Double,
    val returnQty: BigDecimal = BigDecimal.ZERO,
)

data class ReturnFormUiState(
    val invoiceCode: String = "",
    val customerName: String? = null,
    val lines: List<ReturnLineUi> = emptyList(),
    val refundMethod: String = "CASH",   // CASH | BANK_TRANSFER | EWALLET
    val reason: String = "",
    val loading: Boolean = false,
    val submitting: Boolean = false,
    val done: ReturnResultDto? = null,
    val error: ApiError? = null,
) {
    val totalRefund: Double
        get() = lines.sumOf { it.returnQty.toDouble() * it.unitPrice }
}

@HiltViewModel
class ReturnFormViewModel @Inject constructor(
    private val repository: ReturnRepository,
    private val res: ResProvider,
) : ViewModel() {
    private val _state = MutableStateFlow(ReturnFormUiState())
    val state: StateFlow<ReturnFormUiState> = _state.asStateFlow()

    private var invoiceId: Long = 0

    fun load(id: Long) {
        invoiceId = id
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.returnable(id)) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        loading = false,
                        invoiceCode = r.data.invoiceCode,
                        customerName = r.data.customerName,
                        lines = r.data.lines.map { l ->
                            ReturnLineUi(
                                invoiceItemId = l.invoiceItemId,
                                name = l.productName,
                                sku = l.productSku,
                                unit = l.unit,
                                returnableQty = BigDecimal(l.returnableQuantity.toString()),
                                unitPrice = l.unitPrice,
                            )
                        },
                    )
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    /** Đặt số lượng trả cho 1 dòng, kẹp trong [0, returnableQty]. */
    fun setQty(index: Int, qty: BigDecimal) {
        _state.update { s ->
            val lines = s.lines.toMutableList()
            val line = lines.getOrNull(index) ?: return@update s
            val clamped = qty.max(BigDecimal.ZERO).min(line.returnableQty)
            lines[index] = line.copy(returnQty = clamped)
            s.copy(lines = lines)
        }
    }

    fun setRefundMethod(m: String) = _state.update { it.copy(refundMethod = m) }
    fun setReason(r: String) = _state.update { it.copy(reason = r) }
    fun clearError() = _state.update { it.copy(error = null) }

    fun submit() {
        val s = _state.value
        val items = s.lines
            .filter { it.returnQty.signum() > 0 }
            .map { ReturnItemInputDto(invoiceItemId = it.invoiceItemId, quantity = it.returnQty.toPlainString()) }
        if (items.isEmpty()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.misc_return_form_select_one))) }
            return
        }
        _state.update { it.copy(submitting = true, error = null) }
        viewModelScope.launch {
            val body = ReturnCreateDto(
                invoiceId = invoiceId,
                items = items,
                refundMethod = s.refundMethod,
                reason = s.reason.trim().ifBlank { null },
            )
            when (val r = repository.create(body)) {
                is ApiResult.Success -> _state.update { it.copy(submitting = false, done = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(submitting = false, error = r.error) }
            }
        }
    }
}
