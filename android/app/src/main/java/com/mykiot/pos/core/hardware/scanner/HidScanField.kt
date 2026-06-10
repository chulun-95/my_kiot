package com.mykiot.pos.core.hardware.scanner

import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.text.input.ImeAction

/**
 * Ô ẩn luôn giữ focus để hứng input từ súng quét HID (hoạt động như bàn phím).
 * Súng gửi chuỗi barcode + Enter → onScanned được gọi, rồi xoá buffer.
 */
@Composable
fun HidScanField(enabled: Boolean, onScanned: (String) -> Unit) {
    if (!enabled) return
    var buffer by remember { mutableStateOf("") }
    val focus = remember { FocusRequester() }
    LaunchedEffect(Unit) { focus.requestFocus() }
    BasicTextField(
        value = buffer,
        onValueChange = { buffer = it },
        modifier = Modifier.focusRequester(focus),
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
        keyboardActions = KeyboardActions(onDone = {
            val code = buffer.trim()
            buffer = ""
            if (code.isNotEmpty()) onScanned(code)
        }),
    )
}
