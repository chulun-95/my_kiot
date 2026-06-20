package com.mykiot.pos.feature.receipt

import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.feature.receipt.basket.ReceiptBasket
import com.mykiot.pos.feature.receipt.data.SupplierLite

data class ReceiptUiState(
    val basket: ReceiptBasket = ReceiptBasket(),
    val query: String = "",
    val searchResults: List<ProductBriefDto> = emptyList(),
    val suppliers: List<SupplierDto> = emptyList(),
    val supplier: SupplierLite? = null,
    // ----- Thanh toán phiếu nhập -----
    val payFull: Boolean = true,                 // mặc định trả đủ → không thành nợ
    val paidAmount: Long = 0,                    // tiền trả khi KHÔNG trả đủ (đồng)
    val paymentMethod: String = "CASH",
    val note: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val lastReceiptCode: String? = null,
    val lastDraftId: Long? = null,               // != null → điều hướng sang màn chi tiết phiếu nhập
    // Luồng thêm mới:
    val showAddSupplier: Boolean = false,        // mở màn thêm NCC
    val unknownBarcode: String? = null,          // != null → hiện dialog confirm "thêm SP mới?"
    val addProductBarcode: String? = null,       // != null → mở màn thêm SP (prefill barcode)
)
