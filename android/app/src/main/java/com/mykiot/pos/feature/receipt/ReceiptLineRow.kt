package com.mykiot.pos.feature.receipt

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.util.formatVnd
import com.mykiot.pos.feature.receipt.basket.ReceiptLine
import java.math.BigDecimal

@Composable
fun ReceiptLineRow(
    line: ReceiptLine,
    onQty: (BigDecimal) -> Unit,
    onCost: (BigDecimal) -> Unit,
    onRemove: () -> Unit,
) {
    fun parse(v: String): BigDecimal? =
        try { if (v.isBlank()) BigDecimal.ZERO else BigDecimal(v) } catch (_: Exception) { null }

    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column(Modifier.width(120.dp)) {
            Text(line.name, maxLines = 1)
            Text(line.unitName)
        }
        OutlinedTextField(
            value = line.quantity.toPlainString(),
            onValueChange = { parse(it)?.let(onQty) },
            label = { Text("SL") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.width(80.dp),
        )
        OutlinedTextField(
            value = line.costPrice.toPlainString(),
            onValueChange = { parse(it)?.let(onCost) },
            label = { Text("Giá vốn") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.width(110.dp),
        )
        IconButton(onClick = onRemove) {
            Icon(Icons.Filled.Delete, contentDescription = "Xóa")
        }
    }
    Text(
        "Thành tiền: ${formatVnd(line.lineTotal())}",
        Modifier.fillMaxWidth().padding(bottom = 6.dp),
    )
}
