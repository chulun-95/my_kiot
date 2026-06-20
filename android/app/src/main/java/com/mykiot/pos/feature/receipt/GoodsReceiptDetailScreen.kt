package com.mykiot.pos.feature.receipt

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.util.formatQty
import com.mykiot.pos.core.util.formatVnd

@Composable
fun GoodsReceiptDetailScreen(
    receiptId: Long,
    onBack: () -> Unit,
    onCompleted: () -> Unit,
    viewModel: GoodsReceiptDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current

    LaunchedEffect(receiptId) { viewModel.load(receiptId) }
    LaunchedEffect(state.completedCode) {
        state.completedCode?.let {
            snackbar.showSnackbar(context.getString(R.string.receipt_received_toast, it))
            onCompleted()
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = { AppHeader(title = stringResource(R.string.receipt_detail_title), onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
    ) { padding ->
        val r = state.receipt
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            if (r != null) {
                Spacer(Modifier.height(8.dp))
                Text(r.code, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text(
                    stringResource(
                        R.string.receipt_detail_subtitle,
                        r.supplierName ?: stringResource(R.string.receipt_no_supplier_short),
                        statusLabel(r.status),
                    ),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(12.dp))

                LazyColumn(Modifier.weight(1f)) {
                    itemsIndexed(r.items) { i, item ->
                        if (i > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                        Row(
                            Modifier.fillMaxWidth().padding(vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    item.productName ?: stringResource(R.string.receipt_product_fallback, item.productId),
                                    fontWeight = FontWeight.Medium, maxLines = 2,
                                )
                                Text(
                                    stringResource(
                                        R.string.receipt_detail_line,
                                        formatQty(item.quantity), item.unitName ?: "", formatVnd(item.costPrice),
                                    ),
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Text(formatVnd(item.lineTotal), fontWeight = FontWeight.SemiBold)
                        }
                    }
                }

                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        SummaryRow(stringResource(R.string.receipt_total), formatVnd(r.total))
                        Spacer(Modifier.height(4.dp))
                        SummaryRow(stringResource(R.string.receipt_paid_amount), formatVnd(r.paidAmount))
                        if (r.status == "DRAFT") {
                            Spacer(Modifier.height(12.dp))
                            Button(
                                enabled = !state.completing,
                                onClick = { viewModel.complete() },
                                shape = RoundedCornerShape(14.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.onSurface,
                                    contentColor = MaterialTheme.colorScheme.surface,
                                ),
                                modifier = Modifier.fillMaxWidth().height(56.dp),
                            ) { Text(stringResource(R.string.receipt_complete), fontWeight = FontWeight.SemiBold) }
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
            }
        }
    }

    LoadingDialog(visible = state.loading || state.completing, message = stringResource(R.string.receipt_processing))
    state.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun SummaryRow(label: String, value: String) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun statusLabel(status: String): String = when (status) {
    "DRAFT" -> stringResource(R.string.receipt_status_draft)
    "COMPLETED" -> stringResource(R.string.receipt_status_completed)
    "CANCELLED" -> stringResource(R.string.receipt_status_cancelled)
    else -> status
}
