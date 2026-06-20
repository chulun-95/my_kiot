package com.mykiot.pos.feature.supplier

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppSearchField
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import com.mykiot.pos.core.util.formatVnd

@Composable
fun SupplierListScreen(
    onBack: () -> Unit,
    onAdd: () -> Unit,
    onEdit: (Long) -> Unit,
    viewModel: SupplierListViewModel = hiltViewModel(),
) {
    val paging by viewModel.paging.collectAsStateWithLifecycle()
    val query by viewModel.query.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = stringResource(R.string.cat_supplier_list_title),
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onAdd,
                shape = RoundedCornerShape(18.dp),
                containerColor = MaterialTheme.colorScheme.onSurface,
                contentColor = MaterialTheme.colorScheme.surface,
            ) {
                Icon(Icons.Filled.Add, contentDescription = stringResource(R.string.cat_supplier_add_action))
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
                placeholder = stringResource(R.string.cat_supplier_search_hint),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            PagedLazyColumn(
                state = paging,
                onLoadMore = viewModel::loadMore,
                key = { it.id },
                emptyText = stringResource(R.string.cat_supplier_empty),
            ) { supplier ->
                SupplierRow(supplier = supplier, onClick = { onEdit(supplier.id) })
            }
        }
    }

    paging.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun SupplierRow(supplier: SupplierDto, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 10.dp)
            .clickable { onClick() },
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .heightIn(min = 72.dp)
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(supplier.name, fontWeight = FontWeight.SemiBold, maxLines = 1)
                Spacer(Modifier.height(2.dp))
                supplier.phone?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Text(
                    stringResource(R.string.cat_supplier_debt_label) + ": " + formatVnd(supplier.totalDebt.toLong()),
                    style = MaterialTheme.typography.labelMedium,
                    color = if (supplier.totalDebt > 0) MaterialTheme.colorScheme.error
                    else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
