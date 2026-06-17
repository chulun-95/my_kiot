package com.mykiot.pos.feature.pos

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.MoneyInput
import com.mykiot.pos.core.util.formatVnd
import java.math.BigDecimal

private val methods = listOf(
    "CASH" to "Tiền mặt",
    "BANK_TRANSFER" to "Chuyển khoản",
    "MOMO" to "MoMo",
    "VNPAY" to "VNPay",
)

@Composable
fun PaymentDialog(
    total: BigDecimal,
    onDismiss: () -> Unit,
    onConfirm: (method: String, amount: BigDecimal, allowDebt: Boolean) -> Unit,
) {
    var method by remember { mutableStateOf("CASH") }
    var amount by remember { mutableLongStateOf(total.setScale(0, java.math.RoundingMode.HALF_UP).toLong()) }
    val paid = BigDecimal(amount)
    val change = (paid - total).max(BigDecimal.ZERO)
    val debt = (total - paid).max(BigDecimal.ZERO)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Thanh toán") },
        text = {
            Column {
                Text("Tổng tiền: ${formatVnd(total)}")
                Spacer(Modifier.height(8.dp))
                MoneyInput(
                    value = amount,
                    onValueChange = { amount = it },
                    label = "Khách đưa",
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                if (change > BigDecimal.ZERO) Text("Thối lại: ${formatVnd(change)}")
                if (debt > BigDecimal.ZERO) Text("Còn nợ: ${formatVnd(debt)}")
                Spacer(Modifier.height(8.dp))
                methods.forEach { (code, label) ->
                    Row(
                        Modifier.fillMaxWidth().height(40.dp)
                            .selectable(selected = method == code, onClick = { method = code }),
                    ) {
                        RadioButton(selected = method == code, onClick = { method = code })
                        Text(label, Modifier.padding(top = 12.dp))
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                onConfirm(method, paid, debt > BigDecimal.ZERO)
            }) { Text("Xác nhận") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Hủy") } },
    )
}
