package com.mykiot.pos.core.ui

import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LocalTextStyle
import androidx.compose.ui.unit.dp

/**
 * Ô nhập tiền kiểu "máy tính tiền" — giống web: mỗi chữ số gõ vào dịch sang trái và
 * tự nhân 100 (đuôi luôn là bội số 100đ). Giá trị làm việc là [Long] (đồng),
 * KHÔNG bao giờ có phần thập phân. Hiển thị có dấu chấm ngăn nghìn + hậu tố "đ".
 *
 * Quy tắc gõ (khớp `MoneyInput.tsx`):
 * - Gõ 1 chữ số d  →  value = value*10 + d*100   (vd: gõ "8","0" → 800 → 8000)
 * - Xoá 1 chữ số   →  value = (value/1000)*100
 * - Dán / sửa nhiều→ value = floorToHundred(số nhập)
 */
@Composable
fun MoneyInput(
    value: Long,
    onValueChange: (Long) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val display = if (value <= 0L) "" else groupThousands(value)
    OutlinedTextField(
        value = display,
        onValueChange = { newText -> onValueChange(applyMoneyEdit(value, newText)) },
        label = { Text(label) },
        enabled = enabled,
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        suffix = { Text("đ", color = MaterialTheme.colorScheme.onSurfaceVariant) },
        textStyle = LocalTextStyle.current.copy(textAlign = TextAlign.End, fontWeight = FontWeight.Medium),
        shape = RoundedCornerShape(14.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = MaterialTheme.colorScheme.onSurface,
            unfocusedBorderColor = MaterialTheme.colorScheme.outline,
            focusedLabelColor = MaterialTheme.colorScheme.onSurface,
            cursorColor = MaterialTheme.colorScheme.onSurface,
        ),
        modifier = modifier,
    )
}

/** "1234567" (Long) → "1.234.567". Chuỗi rỗng nếu ≤ 0 (để placeholder hiện). */
internal fun moneyDisplay(v: Long): String =
    if (v <= 0L) "" else groupThousands(v)

private fun groupThousands(v: Long): String =
    v.toString().reversed().chunked(3).joinToString(".").reversed()

private fun floorToHundred(n: Long): Long = (n / 100L) * 100L

/** Áp quy tắc gõ tiền kiểu máy tính tiền cho 1 lần sửa text. Dùng chung cho mọi ô nhập tiền. */
internal fun applyMoneyEdit(old: Long, newText: String): Long {
    val newDigits = newText.filter(Char::isDigit)
    val oldDigits = if (old <= 0L) "" else old.toString()
    val v = when {
        newDigits.isEmpty() -> 0L
        // Thêm 1 chữ số ở cuối → dịch trái + ×100
        newDigits.length == oldDigits.length + 1 -> old * 10L + (newDigits.last() - '0') * 100L
        // Xoá 1 chữ số ở cuối
        newDigits.length == oldDigits.length - 1 -> (old / 1000L) * 100L
        // Dán / sửa hàng loạt → làm tròn xuống bội số 100
        else -> floorToHundred(newDigits.toLongOrNull() ?: 0L)
    }
    return v.coerceAtLeast(0L)
}
