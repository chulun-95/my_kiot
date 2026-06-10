package com.mykiot.pos.feature.receipt

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
import androidx.compose.material3.OutlinedButton
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
import java.math.BigDecimal

@Composable
fun ReceiptScreen(viewModel: ReceiptViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var showScanner by remember { mutableStateOf(false) }
    var showSupplier by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.loadSuppliers() }

    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }
    LaunchedEffect(state.lastReceiptCode) {
        state.lastReceiptCode?.let {
            snackbar.showSnackbar("Đã nhập kho: $it")
            viewModel.consumeReceiptCode()
        }
    }

    if (showScanner) {
        MlKitScannerScreen(
            onScanned = { code -> showScanner = false; viewModel.onBarcodeScanned(code) },
            onClose = { showScanner = false },
        )
        return
    }

    if (showSupplier) {
        SupplierPickerDialog(
            suppliers = state.suppliers,
            onPick = { viewModel.setSupplier(it); showSupplier = false },
            onDismiss = { showSupplier = false },
        )
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(12.dp)) {
            HidScanField(enabled = !showScanner, onScanned = viewModel::onBarcodeScanned)

            OutlinedButton(onClick = { showSupplier = true }, modifier = Modifier.fillMaxWidth()) {
                Text(state.supplier?.name ?: "Chọn nhà cung cấp")
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = state.query,
                    onValueChange = viewModel::onQueryChange,
                    label = { Text("Tìm sản phẩm để nhập") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { showScanner = true }) {
                    Icon(Icons.Filled.QrCodeScanner, contentDescription = "Quét mã")
                }
            }

            if (state.searchResults.isNotEmpty()) {
                LazyColumn(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    itemsIndexed(state.searchResults) { _, p ->
                        TextButton(onClick = { viewModel.addFromSearch(p) }) { Text(p.name) }
                    }
                }
            }

            Text("Sản phẩm nhập", Modifier.padding(top = 8.dp))
            LazyColumn(Modifier.weight(1f)) {
                itemsIndexed(state.basket.lines) { index, line ->
                    ReceiptLineRow(
                        line = line,
                        onQty = { viewModel.setQuantity(index, it) },
                        onCost = { viewModel.setCost(index, it) },
                        onRemove = { viewModel.removeLine(index) },
                    )
                }
            }

            Row(
                Modifier.fillMaxWidth().padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Tổng: ${formatVnd(state.basket.total())}")
                Button(
                    enabled = !state.loading && !state.basket.isEmpty(),
                    onClick = { viewModel.submit(BigDecimal.ZERO, "CASH") },
                ) { Text("Hoàn tất nhập") }
            }
        }
    }
}
