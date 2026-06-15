package com.mykiot.pos.feature.account

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.LoadingDialog
import com.mykiot.pos.core.ui.Spacing

@Composable
fun ChangePasswordScreen(
    onBack: () -> Unit,
    onDone: () -> Unit,
    viewModel: ChangePasswordViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(state.errorMessage) {
        state.errorMessage?.let { snackbar.showSnackbar(it); viewModel.clearError() }
    }
    LaunchedEffect(state.done) { if (state.done) onDone() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = { AppHeader(title = "Đổi mật khẩu", onBack = onBack, modifier = Modifier.padding(horizontal = 16.dp)) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.lg, vertical = Spacing.lg),
        ) {
            AppTextField(
                value = state.current,
                onValueChange = viewModel::onCurrent,
                label = "Mật khẩu hiện tại",
                keyboardType = KeyboardType.Password,
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(Spacing.md))
            AppTextField(
                value = state.newPass,
                onValueChange = viewModel::onNew,
                label = "Mật khẩu mới",
                keyboardType = KeyboardType.Password,
                visualTransformation = PasswordVisualTransformation(),
                supporting = "Tối thiểu 6 ký tự",
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(Spacing.md))
            AppTextField(
                value = state.confirm,
                onValueChange = viewModel::onConfirm,
                label = "Xác nhận mật khẩu mới",
                keyboardType = KeyboardType.Password,
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(Spacing.xl))
            Button(
                onClick = viewModel::submit,
                enabled = !state.saving,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.onSurface,
                    contentColor = MaterialTheme.colorScheme.surface,
                ),
                modifier = Modifier.fillMaxWidth().height(56.dp),
            ) { Text("Đổi mật khẩu", fontWeight = FontWeight.SemiBold) }
        }
    }

    LoadingDialog(visible = state.saving, message = "Đang đổi mật khẩu...")
}
