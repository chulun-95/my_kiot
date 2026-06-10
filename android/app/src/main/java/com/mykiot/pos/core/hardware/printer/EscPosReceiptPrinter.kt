package com.mykiot.pos.core.hardware.printer

import android.content.Context
import com.dantsu.escposprinter.EscPosPrinter
import com.dantsu.escposprinter.connection.bluetooth.BluetoothConnection
import com.dantsu.escposprinter.connection.bluetooth.BluetoothPrintersConnections
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class EscPosReceiptPrinter @Inject constructor(
    @ApplicationContext private val context: Context,
) : ReceiptPrinter {

    private val prefs = context.getSharedPreferences("printer_prefs", Context.MODE_PRIVATE)

    override fun savedPrinterMac(): String? = prefs.getString(KEY_MAC, null)
    override fun savePrinterMac(mac: String) { prefs.edit().putString(KEY_MAC, mac).apply() }

    override suspend fun print(data: ReceiptData): PrintResult = withContext(Dispatchers.IO) {
        try {
            val connection: BluetoothConnection = resolveConnection()
                ?: return@withContext PrintResult.Error(
                    "Chưa kết nối máy in. Vui lòng chọn máy in trong Cài đặt.",
                )
            // 58mm giấy ~ 48mm in được, ~203dpi, 32 ký tự/dòng
            val printer = EscPosPrinter(connection, 203, 48f, 32)
            val text = ReceiptLayout.render(data, width = 32)
                .joinToString("\n") { escape(it) }
            printer.printFormattedTextAndCut(text)
            PrintResult.Ok
        } catch (e: Exception) {
            PrintResult.Error("In bill thất bại: ${e.message ?: "lỗi không xác định"}")
        }
    }

    private fun resolveConnection(): BluetoothConnection? {
        val mac = savedPrinterMac()
        val all = BluetoothPrintersConnections().list?.toList().orEmpty()
        return if (mac != null) {
            all.firstOrNull { it.device.address == mac } ?: all.firstOrNull()
        } else {
            BluetoothPrintersConnections.selectFirstPaired()
        }
    }

    // DantSu formatter dùng '[' cho lệnh format; thay tối thiểu để không vỡ layout.
    private fun escape(s: String): String = s.replace("[", "(")

    private companion object { const val KEY_MAC = "printer_mac" }
}
