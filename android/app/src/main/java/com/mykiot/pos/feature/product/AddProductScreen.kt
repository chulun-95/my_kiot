package com.mykiot.pos.feature.product

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.hardware.scanner.MlKitScannerScreen
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.MoneyInput
import com.mykiot.pos.feature.supplier.FormTopBar

/**
 * Màn thêm / sửa sản phẩm.
 *
 * Hai chế độ:
 * - Thêm mới (productId == null): mở từ danh sách SP hoặc từ luồng quét mã lạ ở tab Nhập
 *   (prefill barcode). Tạo xong → trả [ProductBriefDto] qua [onCreated] để thêm thẳng vào phiếu nhập.
 * - Sửa (productId != null): nạp dữ liệu hiện tại qua [AddProductViewModel.startEdit], lưu xong → [onSaved].
 */
@Composable
fun AddProductScreen(
    initialBarcode: String = "",
    productId: Long? = null,
    onCreated: (ProductBriefDto) -> Unit = {},
    onSaved: () -> Unit = {},
    onCancel: () -> Unit,
    viewModel: AddProductViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showScanner by remember { mutableStateOf(false) }
    var showCategoryMenu by remember { mutableStateOf(false) }
    var showStatusMenu by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.loadCategories() }
    LaunchedEffect(productId) {
        if (productId != null) viewModel.startEdit(productId) else viewModel.prefillBarcode(initialBarcode)
    }
    LaunchedEffect(state.created) {
        state.created?.let(onCreated)
    }
    LaunchedEffect(state.saved) {
        if (state.saved) onSaved()
    }

    if (showScanner) {
        MlKitScannerScreen(
            onScanned = { code -> showScanner = false; viewModel.onBarcode(code) },
            onClose = { showScanner = false },
        )
        return
    }

    val statusOptions = listOf(
        "ACTIVE" to stringResource(R.string.cat_product_status_active),
        "INACTIVE" to stringResource(R.string.cat_product_status_inactive),
        "DRAFT" to stringResource(R.string.cat_product_status_draft),
    )
    val title = stringResource(if (state.editingId != null) R.string.cat_product_edit else R.string.cat_product_add)

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            FormTopBar(title = title, onBack = onCancel)

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
            Spacer(Modifier.height(12.dp))
            Box {
                DropdownField(
                    label = stringResource(R.string.cat_product_field_category),
                    selectedText = state.categoryLabel.ifBlank { stringResource(R.string.cat_product_field_category_none) },
                    onClick = { showCategoryMenu = true },
                    modifier = Modifier.fillMaxWidth(),
                )
                DropdownMenu(expanded = showCategoryMenu, onDismissRequest = { showCategoryMenu = false }) {
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.cat_product_field_category_none)) },
                        onClick = { viewModel.onCategory(null, ""); showCategoryMenu = false },
                    )
                    state.categories.forEach { c ->
                        DropdownMenuItem(
                            text = { Text(c.label) },
                            onClick = { viewModel.onCategory(c.id, c.label); showCategoryMenu = false },
                        )
                    }
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                AppTextField(
                    value = state.minStock,
                    onValueChange = viewModel::onMinStock,
                    label = stringResource(R.string.cat_product_field_min_stock),
                    keyboardType = KeyboardType.Number,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                Box(Modifier.weight(1f)) {
                    DropdownField(
                        label = stringResource(R.string.cat_product_field_status),
                        selectedText = statusOptions.first { it.first == state.status }.second,
                        onClick = { showStatusMenu = true },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    DropdownMenu(expanded = showStatusMenu, onDismissRequest = { showStatusMenu = false }) {
                        statusOptions.forEach { (value, label) ->
                            DropdownMenuItem(
                                text = { Text(label) },
                                onClick = { viewModel.onStatus(value); showStatusMenu = false },
                            )
                        }
                    }
                }
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
    state.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

/** Ô dạng field chỉ đọc, bấm để mở [DropdownMenu] neo ngay bên dưới (nhóm hàng / trạng thái). */
@Composable
private fun DropdownField(
    label: String,
    selectedText: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(4.dp))
        Row(
            Modifier
                .fillMaxWidth()
                .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(14.dp))
                .clickable(onClick = onClick)
                .padding(horizontal = 16.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(selectedText, modifier = Modifier.weight(1f))
            Icon(Icons.Filled.ArrowDropDown, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
