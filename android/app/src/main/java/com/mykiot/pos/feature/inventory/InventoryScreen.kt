package com.mykiot.pos.feature.inventory

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.math.BigDecimal

@Composable
fun InventoryScreen(viewModel: InventoryViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.load() }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }

    state.movementsFor?.let { item ->
        MovementsDialog(item = item, movements = state.movements, onDismiss = viewModel::closeMovements)
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(12.dp)) {
            OutlinedTextField(
                value = state.query,
                onValueChange = viewModel::onQueryChange,
                label = { Text("Tìm sản phẩm") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            LazyColumn(Modifier.fillMaxSize().padding(top = 8.dp)) {
                itemsIndexed(state.items) { _, it ->
                    val qty = it.quantity.toBigDecimalOrZero()
                    val low = qty <= BigDecimal(it.minStock)
                    Row(
                        Modifier.fillMaxWidth().clickable { viewModel.openMovements(it) }
                            .padding(vertical = 8.dp),
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(it.productName)
                            Text("${it.productSku} • ${it.unit}")
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Tồn: ${it.quantity}")
                            if (low) Text("Sắp hết", color = MaterialTheme.colorScheme.error)
                        }
                    }
                }
            }
        }
    }
}

private fun String.toBigDecimalOrZero(): BigDecimal =
    try { BigDecimal(this) } catch (_: Exception) { BigDecimal.ZERO }
