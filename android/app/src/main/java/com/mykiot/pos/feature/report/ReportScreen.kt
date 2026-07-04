package com.mykiot.pos.feature.report

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.TrendingUp
import androidx.compose.material.icons.outlined.DateRange
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
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
import com.mykiot.pos.core.network.dto.EodMethodRowDto
import com.mykiot.pos.core.network.dto.RevenuePointDto
import com.mykiot.pos.core.ui.AppDateRangePickerDialog
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
import com.mykiot.pos.core.util.fullDayLabel
import com.mykiot.pos.core.util.rangeLabel
import com.mykiot.pos.core.util.shortDayLabel

@Composable
fun ReportScreen(
    onOpenInventory: () -> Unit = {},
    viewModel: ReportViewModel = hiltViewModel(),
) {
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
                SectionHeader(stringResource(R.string.misc_report_today))
                Spacer(Modifier.height(Spacing.md))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    KpiTile(Icons.AutoMirrored.Outlined.TrendingUp, stringResource(R.string.misc_report_revenue), formatVnd(d.todayRevenue), Modifier.weight(1f))
                    KpiTile(Icons.Outlined.Description, stringResource(R.string.misc_report_invoice_count), d.todayInvoices.toString(), Modifier.weight(1f))
                }
                Spacer(Modifier.height(Spacing.md))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    KpiTile(Icons.Outlined.Group, stringResource(R.string.misc_report_customers), d.todayCustomers.toString(), Modifier.weight(1f))
                    KpiTile(
                        Icons.Outlined.Inventory2, stringResource(R.string.misc_report_low_stock), d.lowStockCount.toString(),
                        Modifier.weight(1f), caption = stringResource(R.string.misc_report_out_of_stock, d.outOfStockCount),
                        onClick = onOpenInventory,
                    )
                }
                d.todayProfit?.let { profit ->
                    Spacer(Modifier.height(Spacing.md))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                        KpiTile(Icons.Outlined.Payments, stringResource(R.string.misc_report_profit), formatVnd(profit), Modifier.weight(1f), accent = DataProfit)
                        Spacer(Modifier.weight(1f))
                    }
                }
            }

            // ===== Doanh thu theo ngày: chọn khoảng + biểu đồ + chi tiết từng ngày =====
            if (state.revenue != null || state.rangeFrom.isNotBlank()) {
                Spacer(Modifier.height(Spacing.xl))
                RevenueSection(
                    state = state,
                    onSelectPreset = viewModel::selectPreset,
                    onCustomRange = viewModel::setCustomRange,
                    onSelectDay = viewModel::selectDay,
                )
            }

            state.eod?.byMethod?.takeIf { it.isNotEmpty() }?.let { rows ->
                Spacer(Modifier.height(Spacing.lg))
                val methodLabels = mapOf(
                    "CASH" to stringResource(R.string.misc_payment_method_cash),
                    "BANK_TRANSFER" to stringResource(R.string.misc_payment_method_bank_transfer),
                    "MOMO" to stringResource(R.string.misc_payment_method_momo),
                    "VNPAY" to stringResource(R.string.misc_payment_method_vnpay),
                )
                val slices = rows.map {
                    DonutSlice(methodLabels[it.method] ?: it.method, paymentValue(it), methodColor(it.method))
                }
                ChartCard(
                    title = stringResource(R.string.misc_report_payment_structure),
                    legend = slices.map { LegendItem(it.label, it.color) },
                ) {
                    DonutChart(slices = slices)
                }
            }

            state.topProducts?.items?.takeIf { it.isNotEmpty() }?.let { items ->
                Spacer(Modifier.height(Spacing.lg))
                ChartCard(title = stringResource(R.string.misc_report_top_products)) {
                    HBarChart(
                        data = items.take(5).map { it.productName to it.revenue },
                        valueLabel = { formatVnd(it.toString()) },
                    )
                }
            }
            Spacer(Modifier.height(Spacing.xl))
        }
    }

    LoadingDialog(visible = state.loading && state.dashboard == null, message = stringResource(R.string.misc_report_loading))
}

@Composable
private fun RevenueSection(
    state: ReportUiState,
    onSelectPreset: (RangePreset) -> Unit,
    onCustomRange: (String, String) -> Unit,
    onSelectDay: (String?) -> Unit,
) {
    var showPicker by remember { mutableStateOf(false) }

    SectionHeader(stringResource(R.string.misc_report_revenue_chart))
    Spacer(Modifier.height(Spacing.md))

    RangeChips(
        selected = state.rangePreset,
        customLabel = if (state.rangePreset == RangePreset.CUSTOM && state.rangeFrom.isNotBlank())
            rangeLabel(state.rangeFrom, state.rangeTo) else stringResource(R.string.misc_report_range_custom),
        onPreset = onSelectPreset,
        onCustom = { showPicker = true },
    )
    Spacer(Modifier.height(Spacing.md))

    val rev = state.revenue
    val series = rev?.series ?: emptyList()

    ChartCard(title = rangeLabel(state.rangeFrom, state.rangeTo)) {
        if (series.isEmpty()) {
            Text(
                stringResource(R.string.misc_report_revenue_empty),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            Column {
                val selectedIndex = series.indexOfFirst { it.period == state.selectedPeriod }.takeIf { it >= 0 }
                ColumnChart(
                    data = series.map { shortDayLabel(it.period) to it.revenue },
                    selectedIndex = selectedIndex,
                    onBarClick = { idx -> onSelectDay(series[idx].period) },
                )
                rev?.let {
                    Spacer(Modifier.height(Spacing.md))
                    Text(
                        stringResource(
                            R.string.misc_report_total_in_range,
                            formatVnd(it.totalRevenue.toLong()),
                            formatVnd(it.totalProfit.toLong()),
                        ),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }

    series.firstOrNull { it.period == state.selectedPeriod }?.let { selected ->
        Spacer(Modifier.height(Spacing.md))
        DayDetailCard(selected)
    }

    if (series.isNotEmpty()) {
        Spacer(Modifier.height(Spacing.lg))
        SectionHeader(stringResource(R.string.misc_report_day_list))
        Spacer(Modifier.height(Spacing.sm))
        series.asReversed().forEach { p ->
            DayRow(point = p, selected = p.period == state.selectedPeriod, onClick = { onSelectDay(p.period) })
            Spacer(Modifier.height(Spacing.sm))
        }
    }

    if (showPicker) {
        AppDateRangePickerDialog(
            title = stringResource(R.string.misc_report_range_picker_title),
            onDismiss = { showPicker = false },
            onConfirm = { from, to -> showPicker = false; onCustomRange(from, to) },
        )
    }
}

@Composable
private fun RangeChips(
    selected: RangePreset,
    customLabel: String,
    onPreset: (RangePreset) -> Unit,
    onCustom: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
    ) {
        FilterChip(
            selected = selected == RangePreset.LAST_7,
            onClick = { onPreset(RangePreset.LAST_7) },
            label = { Text(stringResource(R.string.misc_report_range_7d)) },
        )
        FilterChip(
            selected = selected == RangePreset.LAST_30,
            onClick = { onPreset(RangePreset.LAST_30) },
            label = { Text(stringResource(R.string.misc_report_range_30d)) },
        )
        FilterChip(
            selected = selected == RangePreset.THIS_MONTH,
            onClick = { onPreset(RangePreset.THIS_MONTH) },
            label = { Text(stringResource(R.string.misc_report_range_month)) },
        )
        FilterChip(
            selected = selected == RangePreset.CUSTOM,
            onClick = onCustom,
            label = { Text(customLabel) },
            leadingIcon = { Icon(Icons.Outlined.DateRange, contentDescription = null) },
        )
    }
}

/** Thẻ chi tiết của ngày đang chọn: doanh thu + lợi nhuận + số hóa đơn. */
@Composable
private fun DayDetailCard(point: RevenuePointDto) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 1.dp,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(Spacing.lg)) {
            Text(
                fullDayLabel(point.period),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(Spacing.md))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.lg)) {
                MetricColumn(
                    label = stringResource(R.string.misc_report_revenue),
                    value = formatVnd(point.revenue.toLong()),
                    modifier = Modifier.weight(1f),
                )
                MetricColumn(
                    label = stringResource(R.string.misc_report_profit),
                    value = formatVnd(point.profit.toLong()),
                    accent = DataProfit,
                    modifier = Modifier.weight(1f),
                )
            }
            Spacer(Modifier.height(Spacing.sm))
            Text(
                stringResource(R.string.misc_report_day_invoices, point.invoices),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun MetricColumn(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    accent: androidx.compose.ui.graphics.Color? = null,
) {
    Column(modifier) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(
            value,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            color = accent ?: MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
        )
    }
}

/** 1 dòng trong danh sách từng ngày: ngày · DT · LN. Bấm để chọn xem chi tiết. */
@Composable
private fun DayRow(point: RevenuePointDto, selected: Boolean, onClick: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = if (selected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface,
        shadowElevation = if (selected) 0.dp else 1.dp,
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = Spacing.lg, vertical = Spacing.md),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                shortDayLabel(point.period),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.weight(1f),
            )
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    "${stringResource(R.string.misc_report_dt_short)} ${formatVnd(point.revenue.toLong())}",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    "${stringResource(R.string.misc_report_ln_short)} ${formatVnd(point.profit.toLong())}",
                    style = MaterialTheme.typography.labelMedium,
                    color = DataProfit,
                )
            }
        }
    }
}

private fun methodColor(m: String) = when (m) {
    "CASH" -> DataCash
    "BANK_TRANSFER" -> DataBank
    "MOMO" -> DataWallet
    else -> DataOther
}

/** Tiền vào theo phương thức trong ngày = total_in. */
private fun paymentValue(row: EodMethodRowDto): Double = row.totalIn.toDoubleOrNull() ?: 0.0
