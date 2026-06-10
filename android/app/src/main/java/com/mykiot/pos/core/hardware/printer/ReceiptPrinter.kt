package com.mykiot.pos.core.hardware.printer

sealed interface PrintResult {
    data object Ok : PrintResult
    data class Error(val message: String) : PrintResult   // tiếng Việt
}

interface ReceiptPrinter {
    /** In bill; trả lỗi tiếng Việt nếu chưa kết nối / thất bại. */
    suspend fun print(data: ReceiptData): PrintResult
    fun savedPrinterMac(): String?
    fun savePrinterMac(mac: String)
}
