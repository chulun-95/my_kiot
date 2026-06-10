package com.mykiot.pos.feature.pos

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
import com.mykiot.pos.feature.pos.cart.CartLine
import java.math.BigDecimal

@Composable
fun CartLineRow(
    line: CartLine,
    onQty: (BigDecimal) -> Unit,
    onRemove: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column(Modifier.width(160.dp)) {
            Text(line.name, maxLines = 1)
            Text("${formatVnd(line.unitPrice)}/${line.unitName}")
        }
        OutlinedTextField(
            value = line.quantity.toPlainString(),
            onValueChange = { v ->
                val q = try { if (v.isBlank()) BigDecimal.ZERO else BigDecimal(v) } catch (_: Exception) { null }
                if (q != null) onQty(q)
            },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.width(90.dp),
        )
        Text(formatVnd(line.lineTotal()))
        IconButton(onClick = onRemove) {
            Icon(Icons.Filled.Delete, contentDescription = "Xóa")
        }
    }
}
