package com.mykiot.pos.feature.inventory

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
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
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.LoadingDialog
import androidx.compose.ui.res.stringResource
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.util.formatQty
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import java.math.BigDecimal

@Composable
fun InventoryScreen(viewModel: InventoryViewModel = hiltViewModel()) {
    val state by viewModel.paging.collectAsStateWithLifecycle()
    val query by viewModel.query.collectAsStateWithLifecycle()
    val movements by viewModel.movements.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var showScanner by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    if (showScanner) {
        MlKitScannerScreen(
            onScanned = { code -> showScanner = false; viewModel.onQueryChange(code) },
            onClose = { showScanner = false },
        )
        return
    }

    movements.item?.let { item ->
        MovementsDialog(item = item, movements = movements.items, onDismiss = viewModel::closeMovements)
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp, vertical = 4.dp)) {
            AppSearchField(
                value = query,
                onValueChange = viewModel::onQueryChange,
                placeholder = stringResource(R.string.inv_search_placeholder),
                modifier = Modifier.fillMaxWidth(),
                trailing = {
                    IconButton(onClick = { showScanner = true }) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = stringResource(R.string.inv_scan_barcode))
                    }
                },
            )
            Spacer(Modifier.height(12.dp))

            PagedLazyColumn(
                state = state,
                onLoadMore = viewModel::loadMore,
                key = { it.productId },
                emptyText = stringResource(R.string.inv_empty),
            ) { it ->
                    val qty = it.quantity.toBigDecimalOrZero()
                    val out = qty.signum() <= 0
                    val low = !out && qty <= BigDecimal(it.minStock)
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp)
                            .clickable { viewModel.openMovements(it) },
                    ) {
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(it.productName, fontWeight = FontWeight.SemiBold, maxLines = 1)
                                Spacer(Modifier.height(2.dp))
                                Text(
                                    stringResource(R.string.inv_sku_unit, it.productSku, it.unit),
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text(formatQty(qty), style = MaterialTheme.typography.titleMedium)
                                when {
                                    out -> {
                                        Spacer(Modifier.height(4.dp))
                                        MonoBadge(stringResource(R.string.inv_badge_out), filled = true)
                                    }
                                    low -> {
                                        Spacer(Modifier.height(4.dp))
                                        MonoBadge(stringResource(R.string.inv_badge_low), filled = false)
                                    }
                                }
                            }
                        }
                    }
                }
        }
    }

    LoadingDialog(visible = state.refreshing && state.items.isEmpty(), message = stringResource(R.string.inv_loading))
}

private fun String.toBigDecimalOrZero(): BigDecimal =
    try { BigDecimal(this) } catch (_: Exception) { BigDecimal.ZERO }
