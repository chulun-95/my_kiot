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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
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
        topBar = { AppHeader(title = p?.name ?: "Sản phẩm", onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.lg, vertical = Spacing.md),
        ) {
            if (p == null) {
                Text(
                    state.errorMessage ?: "Đang tải...",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                InfoRow("Mã SKU", p.sku)
                p.barcode?.let { InfoRow("Mã vạch", it) }
                InfoRow("Đơn vị", p.unit)
                InfoRow("Giá bán", formatVnd(p.salePrice.toLong()))
                p.costPrice?.let { InfoRow("Giá vốn", formatVnd(it.toLong())) }
                InfoRow("Trạng thái", if (p.status == "ACTIVE") "Đang bán" else "Ngừng bán")
                InfoRow("Cho phép âm kho", if (p.allowNegative) "Có" else "Không")
                if (p.units.isNotEmpty()) {
                    Spacer(Modifier.height(Spacing.lg))
                    SectionHeader("Đơn vị quy đổi")
                    Spacer(Modifier.height(Spacing.sm))
                    p.units.forEach { u ->
                        InfoRow(u.unitName, "× ${u.conversionRate}")
                    }
                }
            }
        }
    }

    LoadingDialog(visible = state.loading && state.product == null, message = "Đang tải sản phẩm...")
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
