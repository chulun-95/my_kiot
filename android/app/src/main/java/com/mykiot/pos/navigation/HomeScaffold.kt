package com.mykiot.pos.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.PointOfSale
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import com.mykiot.pos.feature.inventory.InventoryScreen
import com.mykiot.pos.feature.pos.PosScreen
import com.mykiot.pos.feature.receipt.ReceiptScreen
import com.mykiot.pos.feature.report.ReportScreen

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab(Routes.TAB_POS, "Bán", Icons.Filled.PointOfSale),
    Tab(Routes.TAB_RECEIPT, "Nhập", Icons.Filled.Receipt),
    Tab(Routes.TAB_INVENTORY, "Tồn", Icons.Filled.Inventory2),
    Tab(Routes.TAB_REPORT, "Báo cáo", Icons.Filled.Assessment),
)

@Composable
fun HomeScaffold(onLogout: () -> Unit) {
    var selected by remember { mutableStateOf(Routes.TAB_POS) }
    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = selected == tab.route,
                        onClick = { selected = tab.route },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when (selected) {
                Routes.TAB_POS -> PosScreen()
                Routes.TAB_RECEIPT -> ReceiptScreen()
                Routes.TAB_INVENTORY -> InventoryScreen()
                Routes.TAB_REPORT -> ReportScreen()
                else -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    val label = tabs.first { it.route == selected }.label
                    Text("Màn '$label'")
                }
            }
        }
    }
}
