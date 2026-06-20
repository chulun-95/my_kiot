package com.mykiot.pos.core.ui

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.mykiot.pos.R

/**
 * Dialog xác nhận dùng chung cho các hành động xoá / không hoàn tác.
 * Nút xác nhận tô màu error để nhấn mạnh tính phá huỷ.
 */
@Composable
fun ConfirmDialog(
    title: String,
    message: String,
    confirmLabel: String = stringResource(R.string.common_delete),
    dismissLabel: String = stringResource(R.string.common_cancel),
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { Text(message) },
        confirmButton = {
            TextButton(
                onClick = { onConfirm(); onDismiss() },
                colors = ButtonDefaults.textButtonColors(
                    contentColor = MaterialTheme.colorScheme.error,
                ),
            ) { Text(confirmLabel) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(dismissLabel) } },
    )
}
