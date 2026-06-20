package com.mykiot.pos.feature.product

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
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
import com.mykiot.pos.core.ui.Spacing
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ProductDetailScreen(
    productId: Long,
    onBack: () -> Unit,
    viewModel: ProductDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(productId) { viewModel.load(productId) }
    val p = state.product

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = { AppHeader(title = p?.name ?: stringResource(R.string.cat_product_title), onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.lg, vertical = Spacing.md),
        ) {
            if (p == null) {
                Text(
                    state.errorMessage ?: stringResource(R.string.cat_product_loading_short),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                InfoRow(stringResource(R.string.cat_product_label_sku), p.sku)
                p.barcode?.let { InfoRow(stringResource(R.string.cat_product_label_barcode), it) }
                InfoRow(stringResource(R.string.cat_product_label_unit), p.unit)
                InfoRow(stringResource(R.string.cat_product_label_sale_price), formatVnd(p.salePrice.toLong()))
                p.costPrice?.let { InfoRow(stringResource(R.string.cat_product_label_cost_price), formatVnd(it.toLong())) }
                InfoRow(
                    stringResource(R.string.cat_product_label_status),
                    if (p.status == "ACTIVE") stringResource(R.string.cat_product_status_active) else stringResource(R.string.cat_product_status_inactive),
                )
                InfoRow(
                    stringResource(R.string.cat_product_label_allow_negative),
                    if (p.allowNegative) stringResource(R.string.cat_product_yes) else stringResource(R.string.cat_product_no),
                )
                if (p.units.isNotEmpty()) {
                    Spacer(Modifier.height(Spacing.lg))
                    SectionHeader(stringResource(R.string.cat_product_units_section))
                    Spacer(Modifier.height(Spacing.sm))
                    p.units.forEach { u ->
                        InfoRow(u.unitName, stringResource(R.string.cat_product_unit_conversion, u.conversionRate))
                    }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading && state.product == null, message = stringResource(R.string.cat_product_loading))
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.Medium)
    }
}
