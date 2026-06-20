package com.mykiot.pos.feature.invoice

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

@Composable
fun InvoiceListScreen(
    viewModel: InvoiceListViewModel = hiltViewModel(),
) {
    val state by viewModel.paging.collectAsStateWithLifecycle()
    val filter by viewModel.filter.collectAsStateWithLifecycle()
    val cancelingId by viewModel.cancelingId.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.load() }

    cancelingId?.let { cancelId ->
        var reason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = viewModel::dismissCancel,
            title = { Text(stringResource(R.string.misc_invoice_cancel_title)) },
            text = {
                Column {
                    Text(stringResource(R.string.misc_invoice_cancel_warning))
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = reason,
                        onValueChange = { reason = it },
                        label = { Text(stringResource(R.string.misc_invoice_cancel_reason_label)) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    enabled = reason.isNotBlank(),
                    onClick = { viewModel.cancelInvoice(cancelId, reason) },
                ) {
                    Text(stringResource(R.string.common_confirm), color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.SemiBold)
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::dismissCancel) { Text(stringResource(R.string.common_close)) }
            },
        )
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                InvoiceFilter.entries.forEach { f ->
                    FilterChip(
                        selected = filter == f,
                        onClick = { viewModel.setFilter(f) },
                        label = { Text(stringResource(f.labelRes())) },
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            PagedLazyColumn(
                state = state,
                onLoadMore = viewModel::loadMore,
                key = { it.id },
                emptyText = stringResource(R.string.misc_invoice_empty),
            ) { inv ->
                InvoiceCard(invoice = inv, onCancel = { viewModel.requestCancel(inv.id) })
            }
        }
    }

    LoadingDialog(visible = state.refreshing && state.items.isEmpty(), message = stringResource(R.string.misc_invoice_loading))
    state.error?.let { com.mykiot.pos.core.ui.ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun InvoiceCard(invoice: InvoiceBriefDto, onCancel: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 10.dp),
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .heightIn(min = 72.dp)
                .padding(horizontal = 14.dp, vertical = 12.dp),
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(invoice.code, fontWeight = FontWeight.SemiBold)
                MonoBadge(
                    text = if (invoice.status == "COMPLETED") stringResource(R.string.misc_invoice_status_sold)
                    else stringResource(R.string.misc_invoice_status_cancelled),
                    filled = invoice.status == "COMPLETED",
                )
            }
            Spacer(Modifier.height(4.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    invoice.customerName ?: stringResource(R.string.common_guest_customer),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    formatDateTime(invoice.completedAt ?: invoice.createdAt),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.height(4.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(formatVnd(invoice.total), fontWeight = FontWeight.SemiBold)
                if (invoice.status == "COMPLETED") {
                    TextButton(onClick = onCancel) {
                        Text(stringResource(R.string.misc_invoice_cancel_action), color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}
