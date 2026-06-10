package com.mykiot.pos.feature.pos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.hardware.printer.PrintResult
import com.mykiot.pos.core.hardware.printer.ReceiptData
import com.mykiot.pos.core.hardware.printer.ReceiptItemLine
import com.mykiot.pos.core.hardware.printer.ReceiptPrinter
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.PaymentInputDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.util.formatVnd
import com.mykiot.pos.feature.pos.data.CustomerLite
import com.mykiot.pos.feature.pos.data.PosRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import javax.inject.Inject

@HiltViewModel
class PosViewModel @Inject constructor(
    private val repository: PosRepository,
    private val printer: ReceiptPrinter,
) : ViewModel() {

    private val _state = MutableStateFlow(PosUiState())
    val state: StateFlow<PosUiState> = _state.asStateFlow()

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

    /** Camera ML Kit hoặc súng HID đều gọi vào đây. */
    fun onBarcodeScanned(code: String) {
        viewModelScope.launch {
            when (val r = repository.byBarcode(code)) {
                is ApiResult.Success -> addToCart(r.data)
                is ApiResult.Failure -> _state.update { it.copy(errorMessage = r.error.message) }
            }
        }
    }

    fun addFromSearch(dto: ProductBriefDto) = addToCart(dto)

    private fun addToCart(dto: ProductBriefDto) {
        val line = repository.toCartLine(dto)
        _state.update {
            it.copy(
                cart = it.cart.addScanned(line),
                errorMessage = null,
                query = "",
                searchResults = emptyList(),
            )
        }
    }

    fun setQuantity(index: Int, qty: BigDecimal) =
        _state.update { it.copy(cart = it.cart.setQuantity(index, qty)) }

    fun setUnitPrice(index: Int, price: BigDecimal) =
        _state.update { it.copy(cart = it.cart.setUnitPrice(index, price)) }

    fun setLineDiscount(index: Int, d: BigDecimal) =
        _state.update { it.copy(cart = it.cart.setLineDiscount(index, d)) }

    fun removeLine(index: Int) =
        _state.update { it.copy(cart = it.cart.removeLine(index)) }

    fun setCustomer(c: CustomerLite?) = _state.update { it.copy(customer = c) }

    fun clearError() = _state.update { it.copy(errorMessage = null) }

    fun consumeInvoiceCode() = _state.update { it.copy(lastInvoiceCode = null, lastInvoice = null) }

    /** In bill cho hoá đơn vừa hoàn tất. Gọi từ UI khi lastInvoice xuất hiện. */
    fun printLastInvoice(shopName: String, shopPhone: String?, footer: String?) {
        val inv = _state.value.lastInvoice ?: return
        val data = ReceiptData(
            shopName = shopName,
            shopPhone = shopPhone,
            invoiceCode = inv.code,
            dateTime = inv.completedAt ?: inv.createdAt,
            lines = inv.items.map {
                ReceiptItemLine(
                    name = it.productName,
                    qty = it.quantity,
                    unitPrice = formatVnd(it.unitPrice),
                    lineTotal = formatVnd(it.lineTotal),
                )
            },
            total = formatVnd(inv.total),
            paid = formatVnd(inv.paidAmount),
            change = formatVnd(inv.changeAmount),
            footer = footer,
        )
        viewModelScope.launch {
            val result = printer.print(data)
            _state.update {
                it.copy(
                    errorMessage = (result as? PrintResult.Error)?.message,
                    lastInvoiceCode = null,
                    lastInvoice = null,
                )
            }
        }
    }

    fun checkout(payments: List<PaymentInputDto>, allowDebt: Boolean) {
        val s = _state.value
        if (s.cart.isEmpty()) {
            _state.update { it.copy(errorMessage = "Giỏ hàng trống") }
            return
        }
        _state.update { it.copy(loading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val r = repository.checkout(s.cart, s.customer?.id, payments, allowDebt)) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        loading = false,
                        cart = it.cart.clear(),
                        customer = null,
                        lastInvoiceCode = r.data.code,
                        lastInvoice = r.data,
                    )
                }
                is ApiResult.Failure ->
                    _state.update { it.copy(loading = false, errorMessage = r.error.message) }
            }
        }
    }
}
