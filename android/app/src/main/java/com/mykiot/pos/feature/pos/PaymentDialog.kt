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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.MoneyInput
import com.mykiot.pos.core.util.formatVnd
import java.math.BigDecimal

@Composable
fun PaymentDialog(
    total: BigDecimal,
    onDismiss: () -> Unit,
    onConfirm: (method: String, amount: BigDecimal, allowDebt: Boolean) -> Unit,
) {
    val methods = listOf(
        "CASH" to stringResource(R.string.pos_method_cash),
        "BANK_TRANSFER" to stringResource(R.string.pos_method_bank_transfer),
        "MOMO" to stringResource(R.string.pos_method_momo),
        "VNPAY" to stringResource(R.string.pos_method_vnpay),
    )
    var method by remember { mutableStateOf("CASH") }
    var amount by remember { mutableLongStateOf(total.setScale(0, java.math.RoundingMode.HALF_UP).toLong()) }
    val paid = BigDecimal(amount)
    val change = (paid - total).max(BigDecimal.ZERO)
    val debt = (total - paid).max(BigDecimal.ZERO)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.pos_payment_title)) },
        text = {
            Column {
                Text(stringResource(R.string.pos_total_amount, formatVnd(total)))
                Spacer(Modifier.height(8.dp))
                MoneyInput(
                    value = amount,
                    onValueChange = { amount = it },
                    label = stringResource(R.string.pos_customer_pays),
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                if (change > BigDecimal.ZERO) Text(stringResource(R.string.pos_change, formatVnd(change)))
                if (debt > BigDecimal.ZERO) Text(stringResource(R.string.pos_debt, formatVnd(debt)))
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
            }) { Text(stringResource(R.string.pos_confirm)) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.pos_cancel)) } },
    )
}
