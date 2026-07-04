package com.mykiot.pos.navigation

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.AssignmentReturn
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.Assessment
import androidx.compose.material.icons.outlined.Category
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.LocalShipping
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.PointOfSale
import androidx.compose.material.icons.outlined.Sell
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.annotation.StringRes
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.AppHeader

private data class HubItem(
    @StringRes val label: Int,
    val route: String,
    val icon: ImageVector,
    val ownerOnly: Boolean = false,   // hướng B dùng để ẩn với CASHIER
)

private data class HubGroup(@StringRes val title: Int, val items: List<HubItem>)

private val hubGroups = listOf(
    HubGroup(
        R.string.core_hub_group_other,
        listOf(
            HubItem(R.string.core_hub_receipt, Routes.RECEIPT, Icons.AutoMirrored.Outlined.ReceiptLong),
            HubItem(R.string.core_hub_inventory, Routes.INVENTORY, Icons.Outlined.Inventory2),
            HubItem(R.string.core_hub_receipt_history, Routes.RECEIPT_HISTORY, Icons.Outlined.History),
            HubItem(R.string.core_hub_returns, Routes.RETURNS, Icons.AutoMirrored.Outlined.AssignmentReturn),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_other,
        listOf(
            HubItem(R.string.core_hub_products, Routes.PRODUCTS, Icons.Outlined.Sell),
            HubItem(R.string.core_hub_customers, Routes.CUSTOMERS, Icons.Outlined.Group),
            HubItem(R.string.core_hub_suppliers, Routes.SUPPLIERS, Icons.Outlined.LocalShipping),
            HubItem(R.string.core_hub_categories, Routes.CATEGORIES, Icons.Outlined.Category),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_other,
        listOf(
            HubItem(R.string.core_hub_invoices, Routes.INVOICE_HISTORY, Icons.Outlined.Description),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_other,
        listOf(
            HubItem(R.string.core_hub_report, Routes.REPORT, Icons.Outlined.Assessment, ownerOnly = true),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_other,
        listOf(
            HubItem(R.string.core_hub_change_password, Routes.CHANGE_PASSWORD, Icons.Outlined.Lock),
        ),
    ),
)

@Composable
fun HubScreen(
    onNavigate: (String) -> Unit,
    onOpenPos: () -> Unit,
    onLogout: () -> Unit,
    viewModel: HubViewModel = hiltViewModel(),
) {
    val user by viewModel.user.collectAsStateWithLifecycle()
    val isOwner = user?.role == "OWNER"
    val visibleGroups = hubGroups
        .map { g -> g.copy(items = g.items.filter { !it.ownerOnly || isOwner }) }
        .filter { it.items.isNotEmpty() }

    var showLogoutConfirm by remember { mutableStateOf(false) }

    if (showLogoutConfirm) {
        AlertDialog(
            onDismissRequest = { showLogoutConfirm = false },
            title = { Text(stringResource(R.string.common_logout)) },
            text = { Text(stringResource(R.string.core_logout_confirm_message)) },
            confirmButton = {
                TextButton(
                    onClick = { showLogoutConfirm = false; onLogout() },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.error,
                    ),
                ) { Text(stringResource(R.string.common_logout)) }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutConfirm = false }) { Text(stringResource(R.string.common_cancel)) }
            },
        )
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = stringResource(R.string.core_hub_title),
                modifier = Modifier.padding(horizontal = 16.dp),
                actions = {
                    TextButton(onClick = { showLogoutConfirm = true }) { Text(stringResource(R.string.common_logout)) }
                },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
        ) {
            PosButton(onClick = onOpenPos)
            Spacer(Modifier.height(20.dp))
            visibleGroups.forEachIndexed { index, group ->
                Text(
                    stringResource(group.title).uppercase(),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Spacer(Modifier.height(10.dp))
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 2000.dp),
                    userScrollEnabled = false,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(group.items, key = { it.route }) { item ->
                        HubCard(item, onClick = { onNavigate(item.route) })
                    }
                }
                if (index != visibleGroups.lastIndex) Spacer(Modifier.height(20.dp))
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun PosButton(onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.primary,
        contentColor = MaterialTheme.colorScheme.onPrimary,
        shadowElevation = 2.dp,
        modifier = Modifier
            .fillMaxWidth()
            .height(76.dp),
    ) {
        Row(
            Modifier
                .fillMaxSize()
                .padding(horizontal = 22.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Outlined.PointOfSale, contentDescription = null)
            Spacer(Modifier.width(14.dp))
            Column {
                Text(stringResource(R.string.core_pos_button_title), style = MaterialTheme.typography.titleLarge)
                Text(
                    stringResource(R.string.core_pos_button_subtitle),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f),
                )
            }
        }
    }
}

@Composable
private fun HubCard(item: HubItem, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        shadowElevation = 1.dp,
        modifier = Modifier
            .fillMaxWidth()
            .height(108.dp),
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .padding(14.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Icon(
                    item.icon,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.size(30.dp),
                )
                Icon(
                    Icons.Outlined.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.outline,
                )
            }
            Text(
                stringResource(item.label),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
