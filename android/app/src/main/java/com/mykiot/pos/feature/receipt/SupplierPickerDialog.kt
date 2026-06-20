package com.mykiot.pos.feature.receipt

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
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
import androidx.compose.ui.unit.dp
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.feature.receipt.data.SupplierLite

@Composable
fun SupplierPickerDialog(
    suppliers: List<SupplierDto>,
    onPick: (SupplierLite?) -> Unit,
    onAddNew: () -> Unit,
    onDismiss: () -> Unit,
) {
    var query by remember { mutableStateOf("") }
    val filtered = remember(query, suppliers) {
        if (query.isBlank()) suppliers
        else suppliers.filter { s ->
            s.name.contains(query, ignoreCase = true) ||
                s.phone?.contains(query) == true
        }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.receipt_pick_supplier)) },
        text = {
            LazyColumn(Modifier.fillMaxWidth()) {
                item {
                    OutlinedTextField(
                        value = query,
                        onValueChange = { query = it },
                        placeholder = { Text(stringResource(R.string.receipt_supplier_search_placeholder)) },
                        leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                        singleLine = true,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 4.dp),
                    )
                }
                item {
                    TextButton(
                        onClick = onAddNew,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Row(
                            Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Start,
                        ) {
                            Icon(Icons.Filled.Add, contentDescription = null)
                            Text(
                                "  " + stringResource(R.string.receipt_add_supplier),
                            )
                        }
                    }
                }
                item {
                    TextButton(onClick = { onPick(null) }, modifier = Modifier.fillMaxWidth()) {
                        Text(
                            stringResource(R.string.receipt_no_supplier),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                itemsIndexed(filtered) { _, s ->
                    TextButton(onClick = { onPick(SupplierLite(s.id, s.name)) }, modifier = Modifier.fillMaxWidth()) {
                        Text(
                            s.name + (s.phone?.let { " ($it)" } ?: ""),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.common_close)) } },
    )
}
