package com.mykiot.pos.core.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DateRangePicker
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDateRangePickerState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.mykiot.pos.R
import com.mykiot.pos.core.util.epochMillisToIsoDate

/**
 * Hộp thoại chọn khoảng ngày dùng chung. Trả về (from, to) dạng "YYYY-MM-DD".
 * Nút xác nhận chỉ bật khi đã chọn đủ cả ngày đầu và ngày cuối.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppDateRangePickerDialog(
    title: String,
    onDismiss: () -> Unit,
    onConfirm: (from: String, to: String) -> Unit,
) {
    val pickerState = rememberDateRangePickerState()
    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            val start = pickerState.selectedStartDateMillis
            val end = pickerState.selectedEndDateMillis
            TextButton(
                onClick = { if (start != null && end != null) onConfirm(epochMillisToIsoDate(start), epochMillisToIsoDate(end)) },
                enabled = start != null && end != null,
            ) { Text(stringResource(R.string.common_confirm)) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.common_cancel)) }
        },
    ) {
        DateRangePicker(
            state = pickerState,
            title = {
                Text(
                    title,
                    modifier = Modifier.padding(start = 16.dp, top = 12.dp),
                    style = MaterialTheme.typography.labelLarge,
                )
            },
            showModeToggle = false,
        )
    }
}
