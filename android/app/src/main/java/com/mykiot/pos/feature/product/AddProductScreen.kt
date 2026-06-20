package com.mykiot.pos.feature.product

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.hardware.scanner.MlKitScannerScreen
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MoneyInput
import com.mykiot.pos.feature.supplier.FormTopBar

/**
 * Màn thêm sản phẩm mới. Mở từ luồng quét mã lạ ở tab Nhập (prefill barcode).
 * Tạo xong → trả [ProductBriefDto] qua [onCreated] để thêm thẳng vào phiếu nhập.
 */
@Composable
fun AddProductScreen(
    initialBarcode: String = "",
    onCreated: (ProductBriefDto) -> Unit,
    onCancel: () -> Unit,
    viewModel: AddProductViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var showScanner by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.prefillBarcode(initialBarcode) }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }
    LaunchedEffect(state.created) {
        state.created?.let(onCreated)
    }

    if (showScanner) {
        MlKitScannerScreen(
            onScanned = { code -> showScanner = false; viewModel.onBarcode(code) },
            onClose = { showScanner = false },
        )
        return
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            FormTopBar(title = stringResource(R.string.cat_product_add), onBack = onCancel)

            AppTextField(
                value = state.name,
                onValueChange = viewModel::onName,
                label = stringResource(R.string.cat_product_field_name),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            AppTextField(
                value = state.barcode,
                onValueChange = viewModel::onBarcode,
                label = stringResource(R.string.cat_product_field_barcode),
                modifier = Modifier.fillMaxWidth(),
                trailingIcon = {
                    IconButton(onClick = { showScanner = true }) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = stringResource(R.string.cat_product_scan_barcode))
                    }
                },
            )
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                AppTextField(
                    value = state.sku,
                    onValueChange = viewModel::onSku,
                    label = stringResource(R.string.cat_product_field_sku),
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                AppTextField(
                    value = state.unit,
                    onValueChange = viewModel::onUnit,
                    label = stringResource(R.string.cat_product_field_unit),
                    modifier = Modifier.width(120.dp),
                )
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                MoneyInput(
                    value = state.costPrice.toLongOrNull() ?: 0L,
                    onValueChange = { viewModel.onCost(it.toString()) },
                    label = stringResource(R.string.cat_product_field_cost),
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                MoneyInput(
                    value = state.salePrice.toLongOrNull() ?: 0L,
                    onValueChange = { viewModel.onSale(it.toString()) },
                    label = stringResource(R.string.cat_product_field_sale),
                    modifier = Modifier.weight(1f),
                )
            }

            Spacer(Modifier.height(24.dp))
            Button(
                onClick = viewModel::submit,
                enabled = !state.loading,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.onSurface,
                    contentColor = MaterialTheme.colorScheme.surface,
                ),
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) { Text(stringResource(R.string.cat_product_save), fontWeight = FontWeight.SemiBold) }
            Spacer(Modifier.height(24.dp))
        }
    }

    LoadingDialog(visible = state.loading, message = stringResource(R.string.cat_product_saving))
}
