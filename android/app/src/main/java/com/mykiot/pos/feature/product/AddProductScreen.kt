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
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.LoadingDialog
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

    LaunchedEffect(Unit) { viewModel.prefillBarcode(initialBarcode) }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }
    LaunchedEffect(state.created) {
        state.created?.let(onCreated)
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            FormTopBar(title = "Thêm sản phẩm", onBack = onCancel)

            AppTextField(
                value = state.name,
                onValueChange = viewModel::onName,
                label = "Tên sản phẩm *",
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            AppTextField(
                value = state.barcode,
                onValueChange = viewModel::onBarcode,
                label = "Mã vạch",
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                AppTextField(
                    value = state.sku,
                    onValueChange = viewModel::onSku,
                    label = "SKU (tự sinh nếu trống)",
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                AppTextField(
                    value = state.unit,
                    onValueChange = viewModel::onUnit,
                    label = "Đơn vị",
                    modifier = Modifier.width(120.dp),
                )
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                AppTextField(
                    value = state.costPrice,
                    onValueChange = viewModel::onCost,
                    label = "Giá nhập",
                    keyboardType = KeyboardType.Number,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(12.dp))
                AppTextField(
                    value = state.salePrice,
                    onValueChange = viewModel::onSale,
                    label = "Giá bán",
                    keyboardType = KeyboardType.Number,
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
            ) { Text("Lưu sản phẩm", fontWeight = FontWeight.SemiBold) }
            Spacer(Modifier.height(24.dp))
        }
    }

    LoadingDialog(visible = state.loading, message = "Đang lưu...")
}
