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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.InventoryItemDto
import com.mykiot.pos.core.network.dto.StockMovementDto
import com.mykiot.pos.core.util.formatDateTime
import com.mykiot.pos.core.util.formatQty

@Composable
private fun typeLabel(type: String): String = when (type) {
    "SALE" -> stringResource(R.string.inv_type_sale)
    "RECEIPT" -> stringResource(R.string.inv_type_receipt)
    "CANCEL_SALE" -> stringResource(R.string.inv_type_cancel_sale)
    "CANCEL_RECEIPT" -> stringResource(R.string.inv_type_cancel_receipt)
    "ADJUSTMENT" -> stringResource(R.string.inv_type_adjustment)
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
        title = { Text(stringResource(R.string.inv_kardex_title, item.productName)) },
        text = {
            if (movements.isEmpty()) {
                Text(stringResource(R.string.inv_no_movements))
            } else {
                LazyColumn(Modifier.fillMaxWidth()) {
                    itemsIndexed(movements) { _, m ->
                        Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                            Text(stringResource(R.string.inv_movement_row, typeLabel(m.type), formatQty(m.quantity), formatQty(m.balanceAfter)))
                            Text(formatDateTime(m.createdAt))
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.common_close)) } },
    )
}
