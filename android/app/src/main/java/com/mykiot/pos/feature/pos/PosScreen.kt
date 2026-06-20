package com.mykiot.pos.feature.pos

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.outlined.Person
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.hardware.scanner.EmbeddedScanner
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MoneyInput
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
    var scanMode by remember { mutableStateOf(false) }
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

    if (state.showCustomerPicker) {
        CustomerPickerDialog(
            results = state.customerResults,
            onSearch = viewModel::searchCustomers,
            onPick = { viewModel.pickCustomer(it) },
            onQuickAdd = { name, phone -> viewModel.quickAddCustomer(name, phone) },
            onDismiss = { viewModel.closeCustomerPicker() },
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp, vertical = 12.dp)) {
            AppHeader(title = stringResource(R.string.pos_title), onBack = onClose) {
                if (state.drafts.isNotEmpty()) {
                    TextButton(onClick = { viewModel.openDrafts() }) {
                        Text(
                            stringResource(R.string.pos_held_orders_count, state.drafts.size),
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
            }
            Spacer(Modifier.height(8.dp))

            if (scanMode) {
                ScanModeContent(
                    state = state,
                    onScanned = { viewModel.onBarcodeScanned(it) },
                    onQty = { i, q -> viewModel.setQuantity(i, q) },
                    onPrice = { i, p -> viewModel.setUnitPrice(i, p) },
                    onDiscount = { i, d -> viewModel.setLineDiscount(i, d) },
                    onRemove = { i -> viewModel.removeLine(i) },
                    onDone = { scanMode = false },
                    modifier = Modifier.weight(1f),
                )
                return@Column
            }

            AppSearchField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                placeholder = stringResource(R.string.pos_search_placeholder),
                modifier = Modifier.fillMaxWidth(),
                trailing = {
                    IconButton(onClick = { scanMode = true }) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = stringResource(R.string.pos_scan_barcode))
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
            CustomerChipRow(
                customerName = state.customer?.name,
                onOpen = { viewModel.openCustomerPicker() },
                onClear = { viewModel.pickCustomer(null) },
            )
            Spacer(Modifier.height(12.dp))
            SectionHeader(stringResource(R.string.pos_cart))
            Spacer(Modifier.height(4.dp))
            LazyColumn(Modifier.weight(1f)) {
                itemsIndexed(state.cart.lines) { index, line ->
                    CartLineRow(
                        line = line,
                        onQty = { viewModel.setQuantity(index, it) },
                        onPrice = { viewModel.setUnitPrice(index, it) },
                        onDiscount = { viewModel.setLineDiscount(index, it) },
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
                        Text(stringResource(R.string.pos_invoice_discount_label), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        MoneyInput(
                            value = state.cart.invoiceDiscount.setScale(0, java.math.RoundingMode.HALF_UP).toLong(),
                            onValueChange = { viewModel.setInvoiceDiscount(java.math.BigDecimal(it)) },
                            label = stringResource(R.string.pos_discount),
                            modifier = Modifier.width(160.dp),
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(stringResource(R.string.pos_grand_total), color = MaterialTheme.colorScheme.onSurfaceVariant)
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
                        ) { Text(stringResource(R.string.pos_hold_order), fontWeight = FontWeight.SemiBold) }
                        Button(
                            enabled = !state.loading && !state.cart.isEmpty(),
                            onClick = { showPayment = true },
                            shape = RoundedCornerShape(14.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.onSurface,
                                contentColor = MaterialTheme.colorScheme.surface,
                            ),
                            modifier = Modifier.weight(1f).height(56.dp),
                        ) { Text(stringResource(R.string.pos_pay), fontWeight = FontWeight.SemiBold) }
                    }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading, message = stringResource(R.string.pos_processing))
}

/**
 * Chế độ quét liên tục: camera 1/3 trên (không đóng sau mỗi lần quét) + danh sách SP đã thêm 2/3 dưới.
 * Nút "Hoàn tất" thoát về màn bán hàng bình thường để thanh toán.
 */
@Composable
private fun ScanModeContent(
    state: PosUiState,
    onScanned: (String) -> Unit,
    onQty: (Int, java.math.BigDecimal) -> Unit,
    onPrice: (Int, java.math.BigDecimal) -> Unit,
    onDiscount: (Int, java.math.BigDecimal) -> Unit,
    onRemove: (Int) -> Unit,
    onDone: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxWidth()) {
        Box(
            Modifier.fillMaxWidth().weight(1f)
                .clip(RoundedCornerShape(16.dp)),
        ) {
            EmbeddedScanner(onScanned = onScanned, modifier = Modifier.fillMaxSize())
            Button(
                onClick = onDone,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.onSurface,
                    contentColor = MaterialTheme.colorScheme.surface,
                ),
                modifier = Modifier.align(Alignment.BottomEnd).padding(12.dp),
            ) { Text(stringResource(R.string.pos_scan_done), fontWeight = FontWeight.SemiBold) }
        }
        Spacer(Modifier.height(8.dp))
        SectionHeader(stringResource(R.string.pos_scan_added_count, state.cart.lines.size))
        Spacer(Modifier.height(4.dp))
        LazyColumn(Modifier.weight(2f)) {
            itemsIndexed(state.cart.lines) { index, line ->
                CartLineRow(
                    line = line,
                    onQty = { onQty(index, it) },
                    onPrice = { onPrice(index, it) },
                    onDiscount = { onDiscount(index, it) },
                    onRemove = { onRemove(index) },
                )
            }
        }
    }
}

/** Hàng chọn khách gọn: chưa chọn → nút "+ Khách"; đã chọn → tên + nút xoá (×). */
@Composable
private fun CustomerChipRow(
    customerName: String?,
    onOpen: () -> Unit,
    onClear: () -> Unit,
) {
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            Modifier.fillMaxWidth().clickable(onClick = onOpen).padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.Person, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.width(10.dp))
            if (customerName == null) {
                Text(stringResource(R.string.pos_guest_customer), color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
                Icon(Icons.Filled.Add, contentDescription = stringResource(R.string.pos_pick_customer), tint = MaterialTheme.colorScheme.onSurface)
                Text(stringResource(R.string.pos_customer_short), fontWeight = FontWeight.SemiBold)
            } else {
                Text(customerName, fontWeight = FontWeight.SemiBold, maxLines = 1, modifier = Modifier.weight(1f))
                IconButton(onClick = onClear) {
                    Icon(Icons.Filled.Close, contentDescription = stringResource(R.string.pos_clear_customer), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun HeldOrdersDialog(
    drafts: List<InvoiceBriefDto>,
    onPick: (Long) -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.pos_held_orders)) },
        text = {
            if (drafts.isEmpty()) {
                Text(stringResource(R.string.pos_no_held_orders), color = MaterialTheme.colorScheme.onSurfaceVariant)
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
                                    stringResource(
                                        R.string.pos_held_order_subtitle,
                                        d.customerName ?: stringResource(R.string.pos_guest_customer),
                                        formatDateTime(d.createdAt),
                                    ),
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
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.pos_close)) } },
    )
}
