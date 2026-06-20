package com.mykiot.pos.feature.receipt

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.ConfirmDialog
import com.mykiot.pos.core.ui.QtyStepper
import com.mykiot.pos.core.ui.applyMoneyEdit
import com.mykiot.pos.core.ui.moneyDisplay
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
    var showRemoveConfirm by remember { mutableStateOf(false) }
    if (showRemoveConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.receipt_remove_product),
            message = stringResource(R.string.receipt_remove_confirm, line.name),
            onConfirm = onRemove,
            onDismiss = { showRemoveConfirm = false },
        )
    }
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp),
    ) {
        Column(Modifier.fillMaxWidth().padding(start = 14.dp, top = 8.dp, end = 6.dp, bottom = 14.dp)) {
            // Tên + nút xoá ở góc trên bên phải
            Row(verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f).padding(top = 6.dp)) {
                    Text(line.name, fontWeight = FontWeight.SemiBold, maxLines = 2)
                    Spacer(Modifier.height(2.dp))
                    Text(
                        line.unitName,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                IconButton(onClick = { showRemoveConfirm = true }) {
                    Icon(
                        Icons.Outlined.DeleteOutline,
                        contentDescription = stringResource(R.string.receipt_remove_product),
                        tint = MaterialTheme.colorScheme.error,
                    )
                }
            }
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    stringResource(R.string.receipt_quantity),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.weight(1f),
                )
                // Xoá hết → 0 (không tự đóng dòng). Dòng SL = 0 sẽ không tính vào phiếu nhập.
                QtyStepper(
                    value = line.quantity,
                    onChange = onQty,
                    min = BigDecimal.ZERO,
                )
            }
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    stringResource(R.string.receipt_cost_price),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.weight(1f),
                )
                CostField(value = line.costPrice, onChange = onCost)
            }
            Spacer(Modifier.height(8.dp))
            Text(
                stringResource(R.string.receipt_line_total, formatVnd(line.lineTotal())),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** Ô giá nhập kiểu tiền: gõ tự ×100, hiển thị có dấu ngăn nghìn, không phần thập phân. */
@Composable
private fun CostField(value: BigDecimal, onChange: (BigDecimal) -> Unit) {
    val current = value.toLong()
    val display = moneyDisplay(current)
    // Ghim con trỏ về cuối — cùng cách sửa với MoneyInput (lỗi "16 → 1000").
    var tfv by remember { mutableStateOf(TextFieldValue(display, TextRange(display.length))) }
    if (tfv.text != display) {
        tfv = TextFieldValue(display, TextRange(display.length))
    }
    Box(
        Modifier
            .width(140.dp)
            .height(44.dp)
            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(10.dp))
            .padding(horizontal = 12.dp),
        contentAlignment = Alignment.CenterEnd,
    ) {
        if (current <= 0L) {
            Text(
                stringResource(R.string.receipt_zero_money),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.End,
            )
        }
        BasicTextField(
            value = tfv,
            onValueChange = { newTfv ->
                val newVal = applyMoneyEdit(current, newTfv.text)
                val newDisplay = moneyDisplay(newVal)
                tfv = TextFieldValue(newDisplay, TextRange(newDisplay.length))
                if (newVal != current) onChange(BigDecimal(newVal))
            },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            textStyle = LocalTextStyle.current.copy(
                fontWeight = FontWeight.Medium,
                textAlign = TextAlign.End,
                color = MaterialTheme.colorScheme.onSurface,
            ),
            cursorBrush = SolidColor(MaterialTheme.colorScheme.onSurface),
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
