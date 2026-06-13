package com.mykiot.pos.feature.receipt

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.LocalShipping
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.hardware.scanner.HidScanField
import com.mykiot.pos.core.hardware.scanner.MlKitScannerScreen
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.SectionHeader
import com.mykiot.pos.core.util.formatVnd
import com.mykiot.pos.feature.product.AddProductScreen
import com.mykiot.pos.feature.supplier.AddSupplierScreen
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

    // ----- Các màn overlay (ưu tiên cao nhất) -----
    if (state.showAddSupplier) {
        AddSupplierScreen(
            initialName = state.query,
            onCreated = { viewModel.onSupplierCreated(it) },
            onCancel = { viewModel.dismissAddSupplier() },
        )
        return
    }
    if (state.addProductBarcode != null) {
        AddProductScreen(
            initialBarcode = state.addProductBarcode!!,
            onCreated = { viewModel.onProductCreated(it) },
            onCancel = { viewModel.cancelAddProduct() },
        )
        return
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
            onAddNew = { showSupplier = false; viewModel.requestAddSupplier() },
            onDismiss = { showSupplier = false },
        )
    }

    // Dialog confirm khi quét mã chưa có trong kho
    state.unknownBarcode?.let { code ->
        AlertDialog(
            onDismissRequest = { viewModel.dismissUnknownBarcode() },
            title = { Text("Sản phẩm chưa có") },
            text = { Text("Mã vạch \"$code\" chưa tồn tại. Bạn có muốn thêm sản phẩm mới không?") },
            confirmButton = {
                TextButton(onClick = { viewModel.confirmAddUnknownProduct() }) {
                    Text("Thêm mới", fontWeight = FontWeight.SemiBold)
                }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.dismissUnknownBarcode() }) { Text("Bỏ qua") }
            },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp, vertical = 4.dp)) {
            HidScanField(enabled = !showScanner, onScanned = viewModel::onBarcodeScanned)

            // Chọn nhà cung cấp
            OutlinedButton(
                onClick = { showSupplier = true },
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
                modifier = Modifier.fillMaxWidth().height(56.dp),
            ) {
                Icon(Icons.Outlined.LocalShipping, contentDescription = null)
                Text(
                    "  " + (state.supplier?.name ?: "Chọn nhà cung cấp"),
                    modifier = Modifier.weight(1f),
                )
                Icon(
                    Icons.Outlined.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.outline,
                )
            }
            Spacer(Modifier.height(12.dp))

            AppSearchField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                placeholder = "Tìm sản phẩm để nhập",
                modifier = Modifier.fillMaxWidth(),
                trailing = {
                    IconButton(onClick = { showScanner = true }) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = "Quét mã")
                    }
                },
            )

            if (state.searchResults.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.surface,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    LazyColumn(Modifier.fillMaxWidth().heightIn(max = 200.dp)) {
                        itemsIndexed(state.searchResults) { i, p ->
                            if (i > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                            Text(
                                p.name,
                                modifier = Modifier.fillMaxWidth()
                                    .clickable { viewModel.addFromSearch(p) }
                                    .padding(horizontal = 14.dp, vertical = 12.dp),
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(16.dp))
            SectionHeader("Sản phẩm nhập")
            Spacer(Modifier.height(4.dp))
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

            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("Tổng nhập", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(formatVnd(state.basket.total()), style = MaterialTheme.typography.titleLarge)
                    }
                    Spacer(Modifier.height(12.dp))
                    Button(
                        enabled = !state.loading && !state.basket.isEmpty(),
                        onClick = { viewModel.submit(BigDecimal.ZERO, "CASH") },
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.onSurface,
                            contentColor = MaterialTheme.colorScheme.surface,
                        ),
                        modifier = Modifier.fillMaxWidth().height(56.dp),
                    ) { Text("Hoàn tất nhập", fontWeight = FontWeight.SemiBold) }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading, message = "Đang lưu phiếu nhập...")
}
