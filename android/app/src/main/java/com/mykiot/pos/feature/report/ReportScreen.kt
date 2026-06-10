package com.mykiot.pos.feature.report

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ReportScreen(viewModel: ReportViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(12.dp).verticalScroll(rememberScrollState()),
        ) {
            Text("Hôm nay", style = MaterialTheme.typography.titleLarge)
            val d = state.dashboard
            if (d != null) {
                StatCard("Doanh thu", formatVnd(d.todayRevenue))
                StatCard("Số hóa đơn", d.todayInvoices.toString())
                StatCard("Khách hàng", d.todayCustomers.toString())
                StatCard("Hóa đơn treo", d.pendingDrafts.toString())
                StatCard("Hàng sắp hết", "${d.lowStockCount} (hết: ${d.outOfStockCount})")
                d.todayProfit?.let { StatCard("Lợi nhuận", formatVnd(it)) }
            } else if (state.loading) {
                Text("Đang tải...")
            }

            state.eod?.let { e ->
                Text("Chốt ca cuối ngày", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 16.dp))
                StatCard("Doanh thu bán hàng", formatVnd(e.salesRevenue))
                StatCard("Số hóa đơn", e.salesInvoices.toString())
                StatCard("Tồn quỹ cuối ngày", formatVnd(e.closingTotal))
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String) {
    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(Modifier.padding(12.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium)
            Text(value, style = MaterialTheme.typography.titleMedium)
        }
    }
}
