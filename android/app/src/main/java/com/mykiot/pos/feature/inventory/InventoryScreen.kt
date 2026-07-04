package com.mykiot.pos.feature.inventory

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
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
import com.mykiot.pos.core.hardware.scanner.MlKitScannerScreen
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import com.mykiot.pos.core.util.formatQty
import java.math.BigDecimal

@Composable
fun InventoryScreen(viewModel: InventoryViewModel = hiltViewModel()) {
    val state by viewModel.paging.collectAsStateWithLifecycle()
    val query by viewModel.query.collectAsStateWithLifecycle()
    val movements by viewModel.movements.collectAsStateWithLifecycle()
    val tab by viewModel.tab.collectAsStateWithLifecycle()
    val lowStock by viewModel.lowStock.collectAsStateWithLifecycle()
    var showScanner by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.load() }

    // ErrorDialog for paging/ALL-tab error
    state.error?.let { ErrorDialog(it) { viewModel.clearError() } }

    // ErrorDialog for LOW-tab error
    lowStock.error?.let { ErrorDialog(it) { viewModel.clearLowStockError() } }

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
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp, vertical = 4.dp)) {

            // TabRow: Tất cả / Sắp hết
            TabRow(selectedTabIndex = tab.ordinal) {
                Tab(
                    selected = tab == InventoryTab.ALL,
                    onClick = { viewModel.selectTab(InventoryTab.ALL) },
                    text = { Text(stringResource(R.string.inventory_tab_all)) },
                )
                Tab(
                    selected = tab == InventoryTab.LOW,
                    onClick = { viewModel.selectTab(InventoryTab.LOW) },
                    text = { Text(stringResource(R.string.inventory_tab_low)) },
                )
            }

            Spacer(Modifier.height(12.dp))

            when (tab) {
                InventoryTab.ALL -> {
                    // Search field only shown in ALL tab
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
                        onRefresh = viewModel::refresh,
                        key = { it.productId },
                        emptyText = stringResource(R.string.inv_empty),
                    ) { item ->
                        InventoryItemRow(item = item, onClick = { viewModel.openMovements(item) })
                    }
                }

                InventoryTab.LOW -> {
                    when {
                        lowStock.loading -> {
                            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                CircularProgressIndicator()
                            }
                        }
                        lowStock.items.isEmpty() -> {
                            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text(
                                    stringResource(R.string.inventory_low_empty),
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                        else -> {
                            LazyColumn {
                                items(lowStock.items, key = { it.productId }) { item ->
                                    InventoryItemRow(item = item, onClick = { viewModel.openMovements(item) })
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

/** Shared row composable for both ALL and LOW tabs. */
@Composable
private fun InventoryItemRow(item: InventoryItemDto, onClick: () -> Unit) {
    val qty = item.quantity.toBigDecimalOrZero()
    val out = qty.signum() <= 0
    val low = !out && qty <= BigDecimal(item.minStock)
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp).clickable { onClick() },
    ) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(item.productName, fontWeight = FontWeight.SemiBold, maxLines = 1)
                Spacer(Modifier.height(2.dp))
                Text(
                    stringResource(R.string.inv_sku_unit, item.productSku, item.unit),
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

private fun String.toBigDecimalOrZero(): BigDecimal =
    try { BigDecimal(this) } catch (_: Exception) { BigDecimal.ZERO }
