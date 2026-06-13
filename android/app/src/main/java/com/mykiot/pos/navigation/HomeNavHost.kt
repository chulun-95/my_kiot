package com.mykiot.pos.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.feature.customer.AddCustomerScreen
import com.mykiot.pos.feature.customer.CustomerDetailScreen
import com.mykiot.pos.feature.customer.CustomerListScreen
import com.mykiot.pos.feature.inventory.InventoryScreen
import com.mykiot.pos.feature.invoice.InvoiceListScreen
import com.mykiot.pos.feature.invoice.ReturnsScreen
import com.mykiot.pos.feature.pos.PosScreen
import com.mykiot.pos.feature.product.ProductListScreen
import com.mykiot.pos.feature.receipt.ReceiptScreen
import com.mykiot.pos.feature.report.ReportScreen

/**
 * Gốc của Home: giữ overlay POS toàn màn (ngoài nav-stack để không phá luồng quét/in),
 * còn lại render [HomeNavHost] (hub + các màn trong).
 */
@Composable
fun HomeRoot(onLogout: () -> Unit) {
    var showPos by remember { mutableStateOf(false) }
    if (showPos) {
        BackHandler { showPos = false }
        PosScreen(onClose = { showPos = false })
        return
    }
    HomeNavHost(onOpenPos = { showPos = true }, onLogout = onLogout)
}

@Composable
private fun HomeNavHost(onOpenPos: () -> Unit, onLogout: () -> Unit) {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = Routes.HUB) {
        composable(Routes.HUB) {
            HubScreen(
                onNavigate = { nav.navigate(it) },
                onOpenPos = onOpenPos,
                onLogout = onLogout,
            )
        }
        composable(Routes.RECEIPT) {
            FeatureScaffold("Nhập hàng", onBack = { nav.popBackStack() }) { ReceiptScreen() }
        }
        composable(Routes.INVENTORY) {
            FeatureScaffold("Tồn kho", onBack = { nav.popBackStack() }) { InventoryScreen() }
        }
        composable(Routes.REPORT) {
            FeatureScaffold("Báo cáo", onBack = { nav.popBackStack() }) { ReportScreen() }
        }

        // ----- Khách hàng (Phase 1) -----
        composable(Routes.CUSTOMERS) {
            CustomerListScreen(
                onBack = { nav.popBackStack() },
                onOpenDetail = { nav.navigate(Routes.customerDetail(it)) },
                onAdd = { nav.navigate(Routes.CUSTOMER_ADD) },
            )
        }
        composable(
            Routes.CUSTOMER_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { backStackEntry ->
            val id = backStackEntry.arguments?.getLong("id") ?: 0L
            CustomerDetailScreen(customerId = id, onBack = { nav.popBackStack() })
        }
        composable(Routes.CUSTOMER_ADD) {
            AddCustomerScreen(
                onCreated = { nav.popBackStack() },
                onCancel = { nav.popBackStack() },
            )
        }

        composable(Routes.PRODUCTS) {
            ProductListScreen(onBack = { nav.popBackStack() })
        }
        composable(Routes.INVOICE_HISTORY) {
            FeatureScaffold("Hóa đơn", onBack = { nav.popBackStack() }) { InvoiceListScreen() }
        }
        composable(Routes.RETURNS) {
            FeatureScaffold("Trả hàng", onBack = { nav.popBackStack() }) { ReturnsScreen() }
        }
        composable(Routes.CHANGE_PASSWORD) { PlaceholderScreen("Đổi mật khẩu", onBack = { nav.popBackStack() }) }
    }
}

/** Khung chuẩn cho một màn trong: header có nút back + back cứng của hệ thống. */
@Composable
private fun FeatureScaffold(
    title: String,
    onBack: () -> Unit,
    content: @Composable () -> Unit,
) {
    BackHandler(onBack = onBack)
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            AppHeader(
                title = title,
                onBack = onBack,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) { content() }
    }
}

@Composable
private fun PlaceholderScreen(title: String, onBack: () -> Unit) {
    FeatureScaffold(title, onBack) {
        Column(Modifier.fillMaxSize().padding(16.dp)) {
            Text("Màn '$title' (đang dựng)")
            Spacer(Modifier.height(12.dp))
            Button(onClick = onBack) { Text("Quay lại") }
        }
    }
}
