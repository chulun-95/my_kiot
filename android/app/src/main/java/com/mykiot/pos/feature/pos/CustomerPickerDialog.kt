package com.mykiot.pos.feature.pos

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import com.mykiot.pos.R
import com.mykiot.pos.feature.pos.data.CustomerLite

/**
 * Dialog chọn khách hàng cho POS: tìm theo tên/SĐT, chọn "Khách lẻ", hoặc thêm nhanh KH mới.
 * Giữ gọn — chỉ hiện danh sách kết quả + 1 vùng "Thêm mới" có thể mở.
 */
@Composable
fun CustomerPickerDialog(
    results: List<CustomerLite>,
    onSearch: (String) -> Unit,
    onPick: (CustomerLite?) -> Unit,
    onQuickAdd: (name: String, phone: String?) -> Unit,
    onDismiss: () -> Unit,
) {
    var query by remember { mutableStateOf("") }
    var addMode by remember { mutableStateOf(false) }
    var newName by remember { mutableStateOf("") }
    var newPhone by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.pos_pick_customer_title)) },
        text = {
            Column {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it; onSearch(it) },
                    label = { Text(stringResource(R.string.pos_search_customer_label)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))

                TextButton(onClick = { onPick(null) }, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.pos_guest_customer_option), modifier = Modifier.fillMaxWidth())
                }

                if (results.isNotEmpty()) {
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    LazyColumn(Modifier.fillMaxWidth().heightIn(max = 240.dp)) {
                        itemsIndexed(results) { i, c ->
                            if (i > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                            Row(
                                Modifier.fillMaxWidth()
                                    .clickable { onPick(c) }
                                    .padding(vertical = 12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(c.name, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
                                if (c.phone != null) {
                                    Text(
                                        c.phone,
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                        }
                    }
                }

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                if (!addMode) {
                    TextButton(
                        onClick = { addMode = true; newName = query },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.pos_add_new_customer), modifier = Modifier.fillMaxWidth()) }
                } else {
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = newName,
                        onValueChange = { newName = it },
                        label = { Text(stringResource(R.string.pos_customer_name_label)) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = newPhone,
                        onValueChange = { newPhone = it },
                        label = { Text(stringResource(R.string.pos_customer_phone_label)) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(8.dp))
                    TextButton(
                        onClick = { onQuickAdd(newName, newPhone) },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.pos_save_customer_and_pick), fontWeight = FontWeight.SemiBold) }
                }
            }
        },
        confirmButton = {},
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.pos_close)) } },
    )
}
