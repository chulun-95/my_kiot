package com.mykiot.pos.feature.pos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.R
import com.mykiot.pos.core.hardware.Beeper
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.hardware.printer.PrintResult
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.hardware.printer.ReceiptData
import com.mykiot.pos.core.hardware.printer.ReceiptItemLine
import com.mykiot.pos.core.hardware.printer.ReceiptPrinter
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.PaymentInputDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.util.formatVnd
import com.mykiot.pos.feature.pos.cart.Cart
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
    private val res: ResProvider,
) : ViewModel() {

    private val _state = MutableStateFlow(PosUiState())
    val state: StateFlow<PosUiState> = _state.asStateFlow()

    fun onQueryChange(q: String) {
        _state.update { it.copy(query = q) }
        if (q.length >= 2) {
            viewModelScope.launch {
                when (val r = repository.search(q)) {
                    is ApiResult.Success -> _state.update { it.copy(searchResults = r.data) }
                    is ApiResult.Failure -> _state.update { it.copy(error = r.error) }
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
                is ApiResult.Success -> {
                    Beeper.pip()  // quét + thêm thành công → "pip"
                    addToCart(r.data)
                }
                is ApiResult.Failure -> {
                    Beeper.error()  // không tìm thấy SP → "tit tit"
                    _state.update { it.copy(error = r.error) }
                }
            }
        }
    }

    fun addFromSearch(dto: ProductBriefDto) = addToCart(dto)

    private fun addToCart(dto: ProductBriefDto) {
        val line = repository.toCartLine(dto)
        _state.update {
            it.copy(
                cart = it.cart.addScanned(line),
                error = null,
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

    fun setInvoiceDiscount(d: BigDecimal) =
        _state.update { it.copy(cart = it.cart.withInvoiceDiscount(d)) }

    fun removeLine(index: Int) =
        _state.update { it.copy(cart = it.cart.removeLine(index)) }

    fun setCustomer(c: CustomerLite?) = _state.update { it.copy(customer = c) }

    // ----- Chọn khách hàng -----
    fun openCustomerPicker() = _state.update { it.copy(showCustomerPicker = true, customerResults = emptyList()) }
    fun closeCustomerPicker() = _state.update { it.copy(showCustomerPicker = false, customerResults = emptyList()) }

    fun searchCustomers(q: String) {
        if (q.isBlank()) {
            _state.update { it.copy(customerResults = emptyList()) }
            return
        }
        viewModelScope.launch {
            when (val r = repository.searchCustomers(q.trim())) {
                is ApiResult.Success -> _state.update { it.copy(customerResults = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(error = r.error) }
            }
        }
    }

    fun pickCustomer(c: CustomerLite?) =
        _state.update { it.copy(customer = c, showCustomerPicker = false, customerResults = emptyList()) }

    /** Thêm nhanh KH rồi chọn luôn cho hoá đơn hiện tại. */
    fun quickAddCustomer(name: String, phone: String?) {
        if (name.isBlank()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.pos_enter_customer_name))) }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.createCustomer(name.trim(), phone)) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        loading = false, customer = r.data,
                        showCustomerPicker = false, customerResults = emptyList(),
                        infoMessage = res.get(R.string.pos_customer_added, r.data.name),
                    )
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(error = null) }

    fun clearInfo() = _state.update { it.copy(infoMessage = null) }

    // ----- Giỏ hàng chờ (hoá đơn treo) -----

    /** Treo đơn hiện tại để rảnh giỏ bán cho khách khác. */
    fun holdOrder() {
        val s = _state.value
        if (s.cart.isEmpty()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.pos_cart_empty))) }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.saveDraft(s.cart, s.customer?.id, s.heldDraftId)) {
                is ApiResult.Success -> {
                    _state.update {
                        it.copy(
                            loading = false,
                            cart = it.cart.clear(),
                            customer = null,
                            heldDraftId = null,
                            infoMessage = res.get(R.string.pos_held_order_done, r.data.code),
                        )
                    }
                    loadDrafts()
                }
                is ApiResult.Failure ->
                    _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun loadDrafts() {
        viewModelScope.launch {
            when (val r = repository.drafts()) {
                is ApiResult.Success -> _state.update { it.copy(drafts = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(error = r.error) }
            }
        }
    }

    fun openDrafts() {
        _state.update { it.copy(showDrafts = true) }
        loadDrafts()
    }

    fun closeDrafts() = _state.update { it.copy(showDrafts = false) }

    /** Khôi phục 1 đơn treo vào giỏ để tiếp tục bán/thanh toán. */
    fun restoreDraft(id: Long) {
        _state.update { it.copy(loading = true, showDrafts = false, error = null) }
        viewModelScope.launch {
            when (val r = repository.getInvoice(id)) {
                is ApiResult.Success -> {
                    val inv = r.data
                    val lines = inv.items.map { repository.toCartLine(it) }
                    val customer = inv.customerId?.let { CustomerLite(it, inv.customerName ?: "", null) }
                    _state.update {
                        it.copy(
                            loading = false,
                            cart = Cart(lines = lines, invoiceDiscount = inv.discountAmount.toBigDecimalOrZero()),
                            customer = customer,
                            heldDraftId = inv.id,
                        )
                    }
                }
                is ApiResult.Failure ->
                    _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

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
                    error = (result as? PrintResult.Error)?.message?.let { msg -> ApiError("PRINT_ERROR", msg) },
                    lastInvoiceCode = null,
                    lastInvoice = null,
                )
            }
        }
    }

    fun checkout(payments: List<PaymentInputDto>, allowDebt: Boolean) {
        val s = _state.value
        if (s.cart.isEmpty()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.pos_cart_empty))) }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.checkout(s.cart, s.customer?.id, s.heldDraftId, payments, allowDebt)) {
                is ApiResult.Success -> _state.update {
                    it.copy(
                        loading = false,
                        cart = it.cart.clear(),
                        customer = null,
                        heldDraftId = null,
                        lastInvoiceCode = r.data.code,
                        lastInvoice = r.data,
                    )
                }
                is ApiResult.Failure -> {
                    if (r.error.code == "INSUFFICIENT_STOCK") Beeper.error()  // hết hàng → "tit tit"
                    _state.update { it.copy(loading = false, error = r.error) }
                }
            }
        }
    }
}

private fun String.toBigDecimalOrZero(): BigDecimal =
    try { BigDecimal(this) } catch (_: Exception) { BigDecimal.ZERO }
