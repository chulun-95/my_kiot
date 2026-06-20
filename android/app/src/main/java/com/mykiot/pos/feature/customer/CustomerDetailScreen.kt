package com.mykiot.pos.feature.customer

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.SectionHeader
import com.mykiot.pos.core.util.formatVnd
import java.math.BigDecimal

@Composable
fun CustomerDetailScreen(
    customerId: Long,
    onBack: () -> Unit,
    viewModel: CustomerDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(customerId) { viewModel.load(customerId) }

    val detail = state.customer
    val c = detail?.customer

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(title = c?.name ?: stringResource(R.string.cat_customer_title), onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp))
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            if (c == null && state.errorMessage != null) {
                Text(
                    state.errorMessage!!,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else if (c != null) {
                InfoRow(stringResource(R.string.cat_customer_label_phone), c.phone ?: "—")
                c.email?.let { InfoRow(stringResource(R.string.cat_customer_label_email), it) }
                c.address?.let { InfoRow(stringResource(R.string.cat_customer_label_address), it) }
                c.note?.let { InfoRow(stringResource(R.string.cat_customer_label_note), it) }
                Spacer(Modifier.height(8.dp))
                Text(
                    stringResource(R.string.cat_customer_spending_summary, formatVnd(BigDecimal.valueOf(c.totalSpent)), c.totalOrders),
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(16.dp))
                SectionHeader(stringResource(R.string.cat_customer_orders_section))
                Spacer(Modifier.height(8.dp))
                if (detail.recentOrders.isEmpty()) {
                    Text(
                        stringResource(R.string.cat_customer_orders_empty),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.labelMedium,
                    )
                } else {
                    LazyColumn(Modifier.fillMaxWidth()) {
                        items(detail.recentOrders, key = { it.invoiceId }) { o ->
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 10.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(o.code, fontWeight = FontWeight.Medium)
                                Text(formatVnd(BigDecimal.valueOf(o.total)))
                            }
                            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                        }
                    }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading, message = stringResource(R.string.cat_customer_loading_short))
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.Medium)
    }
}
