package com.mykiot.pos.feature.inventory

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.network.dto.StockMovementDto

private fun typeLabel(type: String): String = when (type) {
    "SALE" -> "Bán"
    "RECEIPT" -> "Nhập"
    "CANCEL_SALE" -> "Hủy bán"
    "CANCEL_RECEIPT" -> "Hủy nhập"
    "ADJUSTMENT" -> "Điều chỉnh"
    else -> type
}

@Composable
fun MovementsDialog(
    item: InventoryItemDto,
    movements: List<StockMovementDto>,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Thẻ kho — ${item.productName}") },
        text = {
            if (movements.isEmpty()) {
                Text("Chưa có giao dịch.")
            } else {
                LazyColumn(Modifier.fillMaxWidth()) {
                    itemsIndexed(movements) { _, m ->
                        Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                            Text("${typeLabel(m.type)}: ${m.quantity} (còn ${m.balanceAfter})")
                            Text(m.createdAt)
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Đóng") } },
    )
}
