package com.mykiot.pos.feature.receipt

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.feature.receipt.data.SupplierLite

@Composable
fun SupplierPickerDialog(
    suppliers: List<SupplierDto>,
    onPick: (SupplierLite?) -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Chọn nhà cung cấp") },
        text = {
            LazyColumn(Modifier.fillMaxWidth()) {
                item {
                    TextButton(onClick = { onPick(null) }) { Text("— Không chọn NCC —") }
                }
                itemsIndexed(suppliers) { _, s ->
                    TextButton(onClick = { onPick(SupplierLite(s.id, s.name)) }) {
                        Text(s.name + (s.phone?.let { " ($it)" } ?: ""))
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Đóng") } },
    )
}
