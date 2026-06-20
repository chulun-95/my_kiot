package com.mykiot.pos.core.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.SearchOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import com.mykiot.pos.R
import com.mykiot.pos.core.network.ApiError

enum class ErrorIconKind { NETWORK, PERMISSION, NOT_FOUND, GENERIC }

/** Suy loại icon từ ApiError — hàm thuần để unit-test không cần Compose. */
fun errorIconKind(error: ApiError): ErrorIconKind = when {
    error.httpStatus == null && error.code == "NETWORK_ERROR" -> ErrorIconKind.NETWORK
    error.httpStatus == 401 || error.httpStatus == 403 -> ErrorIconKind.PERMISSION
    error.httpStatus == 404 -> ErrorIconKind.NOT_FOUND
    else -> ErrorIconKind.GENERIC
}

private fun ErrorIconKind.icon(): ImageVector = when (this) {
    ErrorIconKind.NETWORK -> Icons.Outlined.CloudOff
    ErrorIconKind.PERMISSION -> Icons.Outlined.Lock
    ErrorIconKind.NOT_FOUND -> Icons.Outlined.SearchOff
    ErrorIconKind.GENERIC -> Icons.Outlined.ErrorOutline
}

/**
 * Dialog hiển thị lỗi dùng chung toàn app (thay Toast/Snackbar).
 * Gồm icon theo loại lỗi, mô tả tiếng Việt, một nút "Đóng".
 */
@Composable
fun ErrorDialog(error: ApiError, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {
            Icon(
                errorIconKind(error).icon(),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.error,
            )
        },
        title = { Text(stringResource(R.string.common_error_title)) },
        text = { Text(error.message) },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.common_close)) }
        },
    )
}
