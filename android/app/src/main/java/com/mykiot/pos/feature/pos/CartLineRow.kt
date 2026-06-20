package com.mykiot.pos.feature.pos

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.ConfirmDialog
import com.mykiot.pos.core.ui.MoneyInput
import com.mykiot.pos.core.ui.QtyStepper
import com.mykiot.pos.core.util.formatVnd
import com.mykiot.pos.feature.pos.cart.CartLine
import java.math.BigDecimal
import java.math.RoundingMode

@Composable
fun CartLineRow(
    line: CartLine,
    onQty: (BigDecimal) -> Unit,
    onPrice: (BigDecimal) -> Unit,
    onDiscount: (BigDecimal) -> Unit,
    onRemove: () -> Unit,
) {
    var showRemoveConfirm by remember { mutableStateOf(false) }
    var showEdit by remember { mutableStateOf(false) }
    if (showRemoveConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.pos_remove_product_title),
            message = stringResource(R.string.pos_remove_product_message, line.name),
            onConfirm = onRemove,
            onDismiss = { showRemoveConfirm = false },
        )
    }
    if (showEdit) {
        LineEditDialog(
            name = line.name,
            unitPrice = line.unitPrice,
            discount = line.discount,
            onConfirm = { price, disc -> onPrice(price); onDiscount(disc) },
            onDismiss = { showEdit = false },
        )
    }
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp),
    ) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Bấm vào tên/giá → mở dialog sửa đơn giá + giảm giá dòng (giữ row gọn).
            Column(Modifier.weight(1f).clickable { showEdit = true }) {
                Text(line.name, fontWeight = FontWeight.SemiBold, maxLines = 1)
                Spacer(Modifier.height(2.dp))
                val priceText = stringResource(R.string.pos_price_per_unit, formatVnd(line.unitPrice), line.unitName)
                Text(
                    if (line.discount.signum() > 0) {
                        stringResource(R.string.pos_price_with_discount, priceText, formatVnd(line.discount))
                    } else {
                        priceText
                    },
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.width(12.dp))
            Text(
                formatVnd(line.lineTotal()),
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.width(12.dp))
            // Giảm về 0 → hỏi xác nhận xoá dòng (không cần nút xoá riêng).
            QtyStepper(
                value = line.quantity,
                onChange = { q -> if (q.signum() <= 0) showRemoveConfirm = true else onQty(q) },
                min = BigDecimal.ZERO,
            )
        }
    }
}

/** Dialog sửa đơn giá + giảm giá cho 1 dòng giỏ hàng. */
@Composable
private fun LineEditDialog(
    name: String,
    unitPrice: BigDecimal,
    discount: BigDecimal,
    onConfirm: (price: BigDecimal, discount: BigDecimal) -> Unit,
    onDismiss: () -> Unit,
) {
    var price by remember { mutableStateOf(unitPrice.setScale(0, RoundingMode.HALF_UP).toLong()) }
    var disc by remember { mutableStateOf(discount.setScale(0, RoundingMode.HALF_UP).toLong()) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(name, maxLines = 2) },
        text = {
            Column {
                MoneyInput(
                    value = price,
                    onValueChange = { price = it },
                    label = stringResource(R.string.pos_unit_price),
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(12.dp))
                MoneyInput(
                    value = disc,
                    onValueChange = { disc = it },
                    label = stringResource(R.string.pos_line_discount),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = {
                onConfirm(BigDecimal(price), BigDecimal(disc))
                onDismiss()
            }) { Text(stringResource(R.string.pos_save), fontWeight = FontWeight.SemiBold) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.pos_cancel)) } },
    )
}
