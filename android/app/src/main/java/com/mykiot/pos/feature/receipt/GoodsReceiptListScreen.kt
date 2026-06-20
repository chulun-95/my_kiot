package com.mykiot.pos.feature.receipt

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
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import com.mykiot.pos.core.network.dto.GoodsReceiptBriefDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.MonoBadge
import com.mykiot.pos.core.ui.paging.PagedLazyColumn
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatVnd

@Composable
fun GoodsReceiptListScreen(
    onBack: () -> Unit,
    onOpenDetail: (Long) -> Unit,
    viewModel: GoodsReceiptListViewModel = hiltViewModel(),
) {
    val paging by viewModel.paging.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = stringResource(R.string.receipt_history_title),
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            PagedLazyColumn(
                state = paging,
                onLoadMore = viewModel::loadMore,
                key = { it.id },
                emptyText = stringResource(R.string.receipt_history_empty),
            ) { r ->
                ReceiptRow(r, onClick = { onOpenDetail(r.id) })
            }
        }
    }

    paging.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun ReceiptRow(r: GoodsReceiptBriefDto, onClick: () -> Unit) {
    val statusText = when (r.status) {
        "COMPLETED" -> stringResource(R.string.receipt_status_completed)
        "CANCELLED" -> stringResource(R.string.receipt_status_cancelled)
        else -> stringResource(R.string.receipt_status_draft)
    }
    Card(
        onClick = onClick,
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
                Text(r.code, fontWeight = FontWeight.SemiBold)
                MonoBadge(
                    text = statusText,
                    filled = r.status == "COMPLETED",
                )
            }
            Spacer(Modifier.height(4.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    r.supplierName ?: stringResource(R.string.receipt_no_supplier_short),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    formatDateTime(r.completedAt ?: r.createdAt),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.height(4.dp))
            Text(formatVnd(r.total), fontWeight = FontWeight.SemiBold)
        }
    }
}
