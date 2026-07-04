package com.mykiot.pos.feature.product

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ProductListScreen(
    onBack: () -> Unit,
    onOpenDetail: (Long) -> Unit,
    onAdd: () -> Unit,
    viewModel: ProductListViewModel = hiltViewModel(),
) {
    val state by viewModel.paging.collectAsStateWithLifecycle()
    val query by viewModel.query.collectAsStateWithLifecycle()
    var showScanner by remember { mutableStateOf(false) }

    if (showScanner) {
        MlKitScannerScreen(
            onScanned = { code -> showScanner = false; viewModel.onQueryChange(code) },
            onClose = { showScanner = false },
        )
        return
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(title = stringResource(R.string.cat_product_title), onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp))
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onAdd,
                shape = RoundedCornerShape(18.dp),
                containerColor = MaterialTheme.colorScheme.onSurface,
                contentColor = MaterialTheme.colorScheme.surface,
            ) {
                Icon(Icons.Filled.Add, contentDescription = stringResource(R.string.cat_product_add))
            }
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            AppSearchField(
                value = query,
                onValueChange = viewModel::onQueryChange,
                placeholder = stringResource(R.string.cat_product_search_placeholder),
                modifier = Modifier.fillMaxWidth(),
                trailing = {
                    IconButton(onClick = { showScanner = true }) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = stringResource(R.string.cat_product_scan_barcode))
                    }
                },
            )
            Spacer(Modifier.height(12.dp))
            PagedLazyColumn(
                state = state,
                onLoadMore = viewModel::loadMore,
                onRefresh = viewModel::refresh,
                key = { it.id },
                emptyText = stringResource(R.string.cat_product_empty),
            ) { p ->
                ProductListCard(p, onClick = { onOpenDetail(p.id) })
            }
        }
    }

    LoadingDialog(visible = state.refreshing && state.items.isEmpty(), message = stringResource(R.string.cat_product_loading))
    state.error?.let { com.mykiot.pos.core.ui.ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun ProductListCard(product: ProductBriefDto, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 10.dp)
            .clickable(onClick = onClick),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .heightIn(min = 72.dp)
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        product.name,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        modifier = Modifier.weight(1f),
                    )
                    if (product.status == "INACTIVE") {
                        Spacer(Modifier.width(6.dp))
                        MonoBadge(stringResource(R.string.cat_product_status_inactive_short), filled = false)
                    }
                }
                Spacer(Modifier.height(2.dp))
                Text(
                    stringResource(R.string.cat_product_list_subtitle, product.sku, product.unit, formatVnd(product.salePrice.toLong())),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Icon(
                Icons.Outlined.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.outline,
            )
        }
    }
}
