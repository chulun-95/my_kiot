package com.mykiot.pos.feature.pos

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
import com.mykiot.pos.core.hardware.scanner.MlKitScannerScreen
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.SectionHeader
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

/** Thông tin shop để in bill — Phase 2 dùng tạm; Phase sau lấy từ /auth/me hoặc cache. */
private const val SHOP_NAME = "CỬA HÀNG"
private const val RECEIPT_FOOTER = "Cảm ơn quý khách!"

@Composable
fun PosScreen(
    onClose: (() -> Unit)? = null,
    viewModel: PosViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var showScanner by remember { mutableStateOf(false) }
    var showPayment by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.loadDrafts() }

    // Hiển thị lỗi tiếng Việt
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let {
            snackbar.showSnackbar(it)
            viewModel.clearError()
        }
    }
    LaunchedEffect(state.infoMessage) {
        state.infoMessage?.let {
            snackbar.showSnackbar(it)
            viewModel.clearInfo()
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

    if (state.showDrafts) {
        HeldOrdersDialog(
            drafts = state.drafts,
            onPick = { viewModel.restoreDraft(it) },
            onDismiss = { viewModel.closeDrafts() },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp, vertical = 12.dp)) {
            AppHeader(title = "Bán hàng", onBack = onClose) {
                if (state.drafts.isNotEmpty()) {
                    TextButton(onClick = { viewModel.openDrafts() }) {
                        Text("Đơn treo (${state.drafts.size})", fontWeight = FontWeight.SemiBold)
                    }
                }
            }
            Spacer(Modifier.height(8.dp))

            AppSearchField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                placeholder = "Tìm sản phẩm (tên / SKU / mã vạch)",
                modifier = Modifier.fillMaxWidth(),
                trailing = {
                    IconButton(onClick = { showScanner = true }) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = "Quét mã")
                    }
                },
            )

            // Kết quả tìm
            if (state.searchResults.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.surface,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    LazyColumn(Modifier.fillMaxWidth().heightIn(max = 220.dp)) {
                        itemsIndexed(state.searchResults) { i, p ->
                            if (i > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                            Row(
                                Modifier.fillMaxWidth()
                                    .clickable { viewModel.addFromSearch(p) }
                                    .padding(horizontal = 14.dp, vertical = 12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(p.name, maxLines = 1, modifier = Modifier.weight(1f))
                                Text(
                                    formatVnd(p.salePrice.toLong()),
                                    fontWeight = FontWeight.SemiBold,
                                )
                            }
                        }
                    }
                }
            }

            Spacer(Modifier.height(16.dp))
            SectionHeader("Giỏ hàng")
            Spacer(Modifier.height(4.dp))
            LazyColumn(Modifier.weight(1f)) {
                itemsIndexed(state.cart.lines) { index, line ->
                    CartLineRow(
                        line = line,
                        onQty = { viewModel.setQuantity(index, it) },
                        onRemove = { viewModel.removeLine(index) },
                    )
                }
            }

            // Thanh tổng + thanh toán
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
                        Text("Tổng cộng", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(
                            formatVnd(state.cart.total()),
                            style = MaterialTheme.typography.titleLarge,
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedButton(
                            enabled = !state.loading && !state.cart.isEmpty(),
                            onClick = { viewModel.holdOrder() },
                            shape = RoundedCornerShape(14.dp),
                            border = BorderStroke(1.dp, MaterialTheme.colorScheme.onSurface),
                            modifier = Modifier.weight(1f).height(56.dp),
                        ) { Text("Treo đơn", fontWeight = FontWeight.SemiBold) }
                        Button(
                            enabled = !state.loading && !state.cart.isEmpty(),
                            onClick = { showPayment = true },
                            shape = RoundedCornerShape(14.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.onSurface,
                                contentColor = MaterialTheme.colorScheme.surface,
                            ),
                            modifier = Modifier.weight(1f).height(56.dp),
                        ) { Text("Thanh toán", fontWeight = FontWeight.SemiBold) }
                    }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading, message = "Đang xử lý...")
}

@Composable
private fun HeldOrdersDialog(
    drafts: List<InvoiceBriefDto>,
    onPick: (Long) -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Đơn treo") },
        text = {
            if (drafts.isEmpty()) {
                Text("Chưa có đơn treo nào", color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                LazyColumn(Modifier.fillMaxWidth().heightIn(max = 360.dp)) {
                    itemsIndexed(drafts) { i, d ->
                        if (i > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                        Row(
                            Modifier.fillMaxWidth()
                                .clickable { onPick(d.id) }
                                .padding(vertical = 12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(d.code, fontWeight = FontWeight.SemiBold, maxLines = 1)
                                Text(
                                    "${d.customerName ?: "Khách lẻ"} · ${formatDateTime(d.createdAt)}",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Text(formatVnd(d.total), fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = { TextButton(onClick = onDismiss) { Text("Đóng") } },
    )
}
