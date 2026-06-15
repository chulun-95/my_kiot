package com.mykiot.pos.feature.supplier

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
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
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.feature.receipt.data.SupplierLite

/**
 * Màn thêm nhà cung cấp mới. Hiển thị toàn màn (overlay) từ luồng chọn NCC ở tab Nhập.
 * Tạo xong → trả [SupplierLite] qua [onCreated] để auto-chọn.
 */
@Composable
fun AddSupplierScreen(
    initialName: String = "",
    onCreated: (SupplierLite) -> Unit,
    onCancel: () -> Unit,
    viewModel: AddSupplierViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) { viewModel.prefillName(initialName) }
    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }
    LaunchedEffect(state.created) {
        state.created?.let { onCreated(SupplierLite(it.id, it.name)) }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            FormTopBar(title = "Thêm nhà cung cấp", onBack = onCancel)

            AppTextField(
                value = state.name,
                onValueChange = viewModel::onName,
                label = "Tên nhà cung cấp *",
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            AppTextField(
                value = state.phone,
                onValueChange = viewModel::onPhone,
                label = "Số điện thoại",
                keyboardType = KeyboardType.Phone,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            AppTextField(
                value = state.address,
                onValueChange = viewModel::onAddress,
                label = "Địa chỉ",
                singleLine = false,
                modifier = Modifier.fillMaxWidth(),
            )

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
            ) { Text("Lưu nhà cung cấp", fontWeight = FontWeight.SemiBold) }
        }
    }

    LoadingDialog(visible = state.loading, message = "Đang lưu...")
}

@Composable
internal fun FormTopBar(title: String, onBack: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Quay lại")
        }
        Spacer(Modifier.width(4.dp))
        Text(title, style = MaterialTheme.typography.titleLarge)
    }
    Spacer(Modifier.height(8.dp))
}
