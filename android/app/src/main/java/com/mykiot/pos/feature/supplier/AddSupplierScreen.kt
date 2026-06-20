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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.ErrorDialog
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.feature.receipt.data.SupplierLite

/**
 * Màn thêm / sửa nhà cung cấp.
 *
 * Hai chế độ:
 * - Thêm mới (supplierId == null): hiển thị từ luồng chọn NCC ở tab Nhập hoặc từ màn danh sách.
 *   Tạo xong → [onCreated] trả [SupplierLite] để auto-chọn (chỉ dùng từ receipt picker).
 * - Sửa (supplierId != null): nạp dữ liệu hiện tại qua [startEdit], lưu xong → [onSaved].
 *
 * [onCreated] giữ default no-op để call-site cũ (ReceiptScreen) không bị phá.
 */
@Composable
fun AddSupplierScreen(
    initialName: String = "",
    supplierId: Long? = null,
    onCreated: (SupplierLite) -> Unit = {},
    onSaved: () -> Unit = {},
    onCancel: () -> Unit,
    viewModel: AddSupplierViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // Khi mở màn: nếu có supplierId → chế độ Sửa; ngược lại prefill tên từ ô tìm kiếm.
    LaunchedEffect(supplierId) {
        if (supplierId != null) viewModel.startEdit(supplierId)
        else viewModel.prefillName(initialName)
    }

    // Phản hồi khi lưu thành công (cả 2 chế độ)
    LaunchedEffect(state.saved) {
        if (state.saved) onSaved()
    }

    // Chỉ chạy khi tạo mới: trả SupplierLite cho receipt picker auto-chọn
    LaunchedEffect(state.created) {
        state.created?.let { onCreated(SupplierLite(it.id, it.name)) }
    }

    // ErrorDialog thay thế Snackbar
    state.error?.let { ErrorDialog(it) { viewModel.clearError() } }

    val title = stringResource(
        if (state.editingId != null) R.string.cat_supplier_edit else R.string.cat_supplier_add,
    )

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            FormTopBar(title = title, onBack = onCancel)

            AppTextField(
                value = state.name,
                onValueChange = viewModel::onName,
                label = stringResource(R.string.cat_supplier_field_name),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            AppTextField(
                value = state.phone,
                onValueChange = viewModel::onPhone,
                label = stringResource(R.string.cat_supplier_field_phone),
                keyboardType = KeyboardType.Phone,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            AppTextField(
                value = state.address,
                onValueChange = viewModel::onAddress,
                label = stringResource(R.string.cat_supplier_field_address),
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
            ) { Text(stringResource(R.string.cat_supplier_save), fontWeight = FontWeight.SemiBold) }
        }
    }

    LoadingDialog(visible = state.loading, message = stringResource(R.string.cat_supplier_saving))
}

@Composable
internal fun FormTopBar(title: String, onBack: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cat_supplier_back))
        }
        Spacer(Modifier.width(4.dp))
        Text(title, style = MaterialTheme.typography.titleLarge)
    }
    Spacer(Modifier.height(8.dp))
}
