package com.mykiot.pos.feature.report

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.TrendingUp
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.network.dto.EodMethodRowDto
import com.mykiot.pos.core.ui.ChartCard
import com.mykiot.pos.core.ui.KpiTile
import com.mykiot.pos.core.ui.LegendItem
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.SectionHeader
import com.mykiot.pos.core.ui.Spacing
import com.mykiot.pos.core.ui.charts.ColumnChart
import com.mykiot.pos.core.ui.charts.DonutChart
import com.mykiot.pos.core.ui.charts.DonutSlice
import com.mykiot.pos.core.ui.charts.HBarChart
import com.mykiot.pos.core.ui.theme.DataBank
import com.mykiot.pos.core.ui.theme.DataCash
import com.mykiot.pos.core.ui.theme.DataOther
import com.mykiot.pos.core.ui.theme.DataProfit
import com.mykiot.pos.core.ui.theme.DataWallet
import com.mykiot.pos.core.util.formatVnd

@Composable
fun ReportScreen(viewModel: ReportViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding)
                .padding(horizontal = Spacing.lg, vertical = Spacing.md)
                .verticalScroll(rememberScrollState()),
        ) {
            val d = state.dashboard
            if (d != null) {
                SectionHeader("Hôm nay")
                Spacer(Modifier.height(Spacing.md))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    KpiTile(Icons.AutoMirrored.Outlined.TrendingUp, "Doanh thu", formatVnd(d.todayRevenue), Modifier.weight(1f))
                    KpiTile(Icons.Outlined.Description, "Số hóa đơn", d.todayInvoices.toString(), Modifier.weight(1f))
                }
                Spacer(Modifier.height(Spacing.md))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    KpiTile(Icons.Outlined.Group, "Khách hàng", d.todayCustomers.toString(), Modifier.weight(1f))
                    KpiTile(
                        Icons.Outlined.Inventory2, "Hàng sắp hết", d.lowStockCount.toString(),
                        Modifier.weight(1f), caption = "hết: ${d.outOfStockCount}",
                    )
                }
                d.todayProfit?.let { profit ->
                    Spacer(Modifier.height(Spacing.md))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                        KpiTile(Icons.Outlined.Payments, "Lợi nhuận", formatVnd(profit), Modifier.weight(1f), accent = DataProfit)
                        Spacer(Modifier.weight(1f))
                    }
                }
            }

            state.revenue7d?.let { rev ->
                Spacer(Modifier.height(Spacing.xl))
                ChartCard(title = "Doanh thu 7 ngày") {
                    ColumnChart(data = rev.series.map { shortDay(it.period) to it.revenue })
                }
            }

            state.eod?.byMethod?.takeIf { it.isNotEmpty() }?.let { rows ->
                Spacer(Modifier.height(Spacing.lg))
                val slices = rows.map { DonutSlice(methodLabel(it.method), paymentValue(it), methodColor(it.method)) }
                ChartCard(
                    title = "Cơ cấu thanh toán",
                    legend = slices.map { LegendItem(it.label, it.color) },
                ) {
                    DonutChart(slices = slices)
                }
            }

            state.topProducts?.items?.takeIf { it.isNotEmpty() }?.let { items ->
                Spacer(Modifier.height(Spacing.lg))
                ChartCard(title = "Top sản phẩm") {
                    HBarChart(
                        data = items.take(5).map { it.productName to it.revenue },
                        valueLabel = { formatVnd(it.toString()) },
                    )
                }
            }
            Spacer(Modifier.height(Spacing.xl))
        }
    }

    LoadingDialog(visible = state.loading && state.dashboard == null, message = "Đang tải báo cáo...")
}

/** "2026-06-13" → "13/6" cho nhãn trục. */
private fun shortDay(period: String): String {
    val parts = period.split("-")
    return if (parts.size == 3) "${parts[2].toInt()}/${parts[1].toInt()}" else period
}

private fun methodLabel(m: String) = when (m) {
    "CASH" -> "Tiền mặt"
    "BANK_TRANSFER" -> "Chuyển khoản"
    "MOMO" -> "MoMo"
    "VNPAY" -> "VNPay"
    else -> m
}

private fun methodColor(m: String) = when (m) {
    "CASH" -> DataCash
    "BANK_TRANSFER" -> DataBank
    "MOMO" -> DataWallet
    else -> DataOther
}

/** Tiền vào theo phương thức trong ngày = total_in. */
private fun paymentValue(row: EodMethodRowDto): Double = row.totalIn.toDoubleOrNull() ?: 0.0
