package com.mykiot.pos.feature.pos

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.hardware.scanner.HidScanField
import com.mykiot.pos.core.hardware.scanner.MlKitScannerScreen
import com.mykiot.pos.core.util.formatVnd

/** Thông tin shop để in bill — Phase 2 dùng tạm; Phase sau lấy từ /auth/me hoặc cache. */
private const val SHOP_NAME = "CỬA HÀNG"
private const val RECEIPT_FOOTER = "Cảm ơn quý khách!"

@Composable
fun PosScreen(viewModel: PosViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var showScanner by remember { mutableStateOf(false) }
    var showPayment by remember { mutableStateOf(false) }

    // Hiển thị lỗi tiếng Việt
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let {
            snackbar.showSnackbar(it)
            viewModel.clearError()
        }
    }
    // Sau checkout thành công → in bill
    LaunchedEffect(state.lastInvoiceCode) {
        if (state.lastInvoiceCode != null) {
            viewModel.printLastInvoice(SHOP_NAME, null, RECEIPT_FOOTER)
        }
    }

    if (showScanner) {
        MlKitScannerScreen(
            onScanned = { code -> showScanner = false; viewModel.onBarcodeScanned(code) },
            onClose = { showScanner = false },
        )
        return
    }

    if (showPayment) {
        PaymentDialog(
            total = state.cart.total(),
            onDismiss = { showPayment = false },
            onConfirm = { method, amount, allowDebt ->
                showPayment = false
                viewModel.checkout(
                    listOf(com.mykiot.pos.core.network.dto.PaymentInputDto(method, amount.toPlainString())),
                    allowDebt,
                )
            },
        )
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(12.dp)) {
            // Ô hứng súng HID (ẩn)
            HidScanField(enabled = !showScanner, onScanned = viewModel::onBarcodeScanned)

            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = state.query,
                    onValueChange = viewModel::onQueryChange,
                    label = { Text("Tìm sản phẩm (tên/SKU/mã vạch)") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { showScanner = true }) {
                    Icon(Icons.Filled.QrCodeScanner, contentDescription = "Quét mã")
                }
            }

            // Kết quả tìm
            if (state.searchResults.isNotEmpty()) {
                LazyColumn(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    itemsIndexed(state.searchResults) { _, p ->
                        TextButton(onClick = { viewModel.addFromSearch(p) }) {
                            Text("${p.name} — ${formatVnd(p.salePrice.toLong())}")
                        }
                    }
                }
            }

            Text("Giỏ hàng", Modifier.padding(top = 8.dp))
            LazyColumn(Modifier.weight(1f)) {
                itemsIndexed(state.cart.lines) { index, line ->
                    CartLineRow(
                        line = line,
                        onQty = { viewModel.setQuantity(index, it) },
                        onRemove = { viewModel.removeLine(index) },
                    )
                }
            }

            Row(
                Modifier.fillMaxWidth().padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Tổng: ${formatVnd(state.cart.total())}")
                Button(
                    enabled = !state.loading && !state.cart.isEmpty(),
                    onClick = { showPayment = true },
                ) { Text("Thanh toán") }
            }
        }
    }
}
