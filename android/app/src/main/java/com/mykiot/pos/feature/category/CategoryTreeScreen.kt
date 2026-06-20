package com.mykiot.pos.feature.category

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mykiot.pos.R
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.AppTextField
import com.mykiot.pos.core.ui.ConfirmDialog
import com.mykiot.pos.core.ui.ErrorDialog

@Composable
fun CategoryTreeScreen(
    onBack: () -> Unit,
    viewModel: CategoryViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var deleteId by remember { mutableStateOf<Long?>(null) }
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = stringResource(R.string.cat_category_title),
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
                actions = {
                    TextButton(onClick = { viewModel.openAdd(null) }) { Text(stringResource(R.string.cat_category_add_root)) }
                },
            )
        },
    ) { padding ->
        if (state.nodes.isEmpty()) {
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(padding),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(stringResource(R.string.cat_category_empty), Modifier.padding(top = 48.dp))
            }
        } else {
            LazyColumn(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 16.dp),
            ) {
                items(state.nodes, key = { it.id }) { parent ->
                    CategoryRow(parent, indent = 0, viewModel = viewModel, onAskDelete = { deleteId = it })
                    parent.children.forEach { child ->
                        CategoryRow(child, indent = 16, viewModel = viewModel, onAskDelete = { deleteId = it })
                    }
                }
            }
        }
    }

    if (state.editorOpen) {
        AlertDialog(
            onDismissRequest = viewModel::closeEditor,
            title = {
                Text(
                    stringResource(
                        if (state.editorEditingId != null) R.string.cat_category_edit
                        else if (state.editorParentId != null) R.string.cat_category_add_child
                        else R.string.cat_category_add_root,
                    ),
                )
            },
            text = {
                AppTextField(
                    value = state.editorName,
                    onValueChange = viewModel::onEditorName,
                    label = stringResource(R.string.cat_category_name_label),
                    modifier = Modifier.fillMaxWidth(),
                )
            },
            confirmButton = { TextButton(onClick = viewModel::saveEditor) { Text(stringResource(R.string.common_save)) } },
            dismissButton = { TextButton(onClick = viewModel::closeEditor) { Text(stringResource(R.string.common_cancel)) } },
        )
    }

    deleteId?.let { id ->
        ConfirmDialog(
            title = stringResource(R.string.cat_category_title),
            message = stringResource(R.string.cat_category_delete_confirm),
            onConfirm = { viewModel.delete(id) },
            onDismiss = { deleteId = null },
        )
    }

    state.error?.let { ErrorDialog(it) { viewModel.clearError() } }
}

@Composable
private fun CategoryRow(
    node: CategoryNodeDto,
    indent: Int,
    viewModel: CategoryViewModel,
    onAskDelete: (Long) -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(start = indent.dp, top = 6.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(node.name, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        if (node.depth == 1) {
            IconButton(onClick = { viewModel.openAdd(node.id) }) {
                Icon(Icons.Outlined.Add, contentDescription = stringResource(R.string.cat_category_add_child))
            }
        }
        IconButton(onClick = { viewModel.openEdit(node.id, node.name) }) {
            Icon(Icons.Outlined.Edit, contentDescription = stringResource(R.string.cat_category_edit))
        }
        IconButton(onClick = { onAskDelete(node.id) }) {
            Icon(Icons.Outlined.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error)
        }
    }
}
