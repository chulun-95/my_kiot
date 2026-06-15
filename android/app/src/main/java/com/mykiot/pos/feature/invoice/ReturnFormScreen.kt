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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.QtyStepper
import com.mykiot.pos.core.ui.SectionHeader
import com.mykiot.pos.core.ui.Spacing
import com.mykiot.pos.core.util.formatVnd
import java.math.BigDecimal

private val refundMethods = listOf(
    "CASH" to "Tiền mặt",
    "BANK_TRANSFER" to "Chuyển khoản",
    "EWALLET" to "Ví điện tử",
)

@Composable
fun ReturnFormScreen(
    invoiceId: Long,
    onBack: () -> Unit,
    onDone: () -> Unit,
    viewModel: ReturnFormViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(invoiceId) { viewModel.load(invoiceId) }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }
    LaunchedEffect(state.done) { if (state.done != null) onDone() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            AppHeader(
                title = if (state.invoiceCode.isBlank()) "Trả hàng" else "Trả hàng · ${state.invoiceCode}",
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        },
        bottomBar = {
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = Spacing.lg, vertical = Spacing.md),
            ) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("Tổng hoàn trả", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(formatVnd(state.totalRefund.toLong()), style = MaterialTheme.typography.titleLarge)
                }
                Spacer(Modifier.height(Spacing.md))
                Button(
                    onClick = viewModel::submit,
                    enabled = !state.submitting && state.totalRefund > 0,
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.onSurface,
                        contentColor = MaterialTheme.colorScheme.surface,
                    ),
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                ) { Text("Xác nhận trả hàng", fontWeight = FontWeight.SemiBold) }
            }
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.lg),
        ) {
            item {
                Spacer(Modifier.height(Spacing.sm))
                SectionHeader("Phương thức hoàn tiền")
                Spacer(Modifier.height(Spacing.sm))
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    refundMethods.forEach { (code, label) ->
                        FilterChip(
                            selected = state.refundMethod == code,
                            onClick = { viewModel.setRefundMethod(code) },
                            label = { Text(label) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.onSurface,
                                selectedLabelColor = MaterialTheme.colorScheme.surface,
                            ),
                        )
                    }
                }
                Spacer(Modifier.height(Spacing.lg))
                SectionHeader("Sản phẩm trả")
                Spacer(Modifier.height(Spacing.sm))
            }

            itemsIndexed(state.lines) { index, line ->
                ReturnLineCard(line = line, onQty = { viewModel.setQty(index, it) })
            }

            item {
                Spacer(Modifier.height(Spacing.sm))
                OutlinedTextField(
                    value = state.reason,
                    onValueChange = viewModel::setReason,
                    label = { Text("Lý do trả (tuỳ chọn)") },
                    singleLine = true,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(Spacing.lg))
            }
        }
    }

    LoadingDialog(visible = state.loading || state.submitting, message = if (state.submitting) "Đang lưu phiếu trả..." else "Đang tải...")
}

@Composable
private fun ReturnLineCard(line: ReturnLineUi, onQty: (BigDecimal) -> Unit) {
    val fullyReturned = line.returnableQty.signum() <= 0
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp),
    ) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(line.name, fontWeight = FontWeight.SemiBold, maxLines = 1)
                Spacer(Modifier.height(2.dp))
                Text(
                    "${line.sku} · còn trả được ${line.returnableQty.toPlainString()} ${line.unit ?: ""}".trim(),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    "${formatVnd(line.unitPrice.toLong())}/${line.unit ?: ""}",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.height(0.dp))
            if (fullyReturned) {
                Text(
                    "Đã trả hết",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                QtyStepper(value = line.returnQty, onChange = onQty, min = BigDecimal.ZERO)
            }
        }
    }
}
