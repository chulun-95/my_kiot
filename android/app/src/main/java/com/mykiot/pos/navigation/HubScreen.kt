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
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.Inventory2
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.core.ui.SectionHeader

private data class HubItem(
    val label: String,
    val route: String,
    val icon: ImageVector,
    val ownerOnly: Boolean = false,   // hướng B dùng để ẩn với CASHIER
)

private data class HubGroup(val title: String, val items: List<HubItem>)

private val hubGroups = listOf(
    HubGroup(
        "Kho",
        listOf(
            HubItem("Nhập hàng", Routes.RECEIPT, Icons.AutoMirrored.Outlined.ReceiptLong),
            HubItem("Tồn kho", Routes.INVENTORY, Icons.Outlined.Inventory2),
            HubItem("Trả hàng", Routes.RETURNS, Icons.AutoMirrored.Outlined.AssignmentReturn),
        ),
    ),
    HubGroup(
        "Danh mục",
        listOf(
            HubItem("Sản phẩm", Routes.PRODUCTS, Icons.Outlined.Sell),
            HubItem("Khách hàng", Routes.CUSTOMERS, Icons.Outlined.Group),
        ),
    ),
    HubGroup(
        "Bán hàng",
        listOf(
            HubItem("Hóa đơn", Routes.INVOICE_HISTORY, Icons.Outlined.Description),
        ),
    ),
    HubGroup(
        "Báo cáo",
        listOf(
            HubItem("Tổng quan", Routes.REPORT, Icons.Outlined.Assessment),
        ),
    ),
    HubGroup(
        "Hệ thống",
        listOf(
            HubItem("Đổi mật khẩu", Routes.CHANGE_PASSWORD, Icons.Outlined.Lock),
        ),
    ),
)

@Composable
fun HubScreen(
    onNavigate: (String) -> Unit,
    onOpenPos: () -> Unit,
    onLogout: () -> Unit,
) {
    var showLogoutConfirm by remember { mutableStateOf(false) }

    if (showLogoutConfirm) {
        AlertDialog(
            onDismissRequest = { showLogoutConfirm = false },
            title = { Text("Đăng xuất") },
            text = { Text("Bạn có chắc chắn muốn đăng xuất không?") },
            confirmButton = {
                TextButton(
                    onClick = { showLogoutConfirm = false; onLogout() },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.error,
                    ),
                ) { Text("Đăng xuất") }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutConfirm = false }) { Text("Hủy") }
            },
        )
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = "my_kiot POS",
                modifier = Modifier.padding(horizontal = 16.dp),
                actions = {
                    TextButton(onClick = { showLogoutConfirm = true }) { Text("Đăng xuất") }
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
            hubGroups.forEachIndexed { index, group ->
                SectionHeader(group.title)
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
                if (index != hubGroups.lastIndex) Spacer(Modifier.height(20.dp))
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
                Text("BÁN HÀNG", style = MaterialTheme.typography.titleLarge)
                Text(
                    "Mở màn POS để bán hàng",
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
            .height(96.dp),
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
                )
                Icon(
                    Icons.Outlined.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.outline,
                )
            }
            Text(
                item.label,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}
