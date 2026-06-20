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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.navigation.NavBackStackEntry
import androidx.navigation.NavController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.mykiot.pos.R
import com.mykiot.pos.core.ui.AppHeader
import com.mykiot.pos.feature.account.ChangePasswordScreen
import com.mykiot.pos.feature.customer.AddCustomerScreen
import com.mykiot.pos.feature.customer.CustomerDetailScreen
import com.mykiot.pos.feature.customer.CustomerListScreen
import com.mykiot.pos.feature.inventory.InventoryScreen
import com.mykiot.pos.feature.invoice.InvoiceListScreen
import com.mykiot.pos.feature.invoice.ReturnFormScreen
import com.mykiot.pos.feature.invoice.ReturnsScreen
import com.mykiot.pos.feature.pos.PosScreen
import com.mykiot.pos.feature.product.AddProductScreen
import com.mykiot.pos.feature.product.ProductDetailScreen
import com.mykiot.pos.feature.product.ProductListScreen
import com.mykiot.pos.feature.receipt.GoodsReceiptDetailScreen
import com.mykiot.pos.feature.receipt.ReceiptScreen
import com.mykiot.pos.feature.report.ReportScreen
import com.mykiot.pos.feature.supplier.AddSupplierScreen
import com.mykiot.pos.feature.supplier.SupplierListScreen

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
        composable(Routes.HUB) { entry ->
            HubScreen(
                onNavigate = { nav.navigateOnce(entry, it) },
                onOpenPos = onOpenPos,
                onLogout = onLogout,
            )
        }
        composable(Routes.RECEIPT) { entry ->
            FeatureScaffold(stringResource(R.string.core_screen_receipt), onBack = { nav.popOnce(entry) }) {
                ReceiptScreen(onCreatedDraft = { nav.navigateOnce(entry, Routes.receiptDetail(it)) })
            }
        }
        composable(
            Routes.RECEIPT_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            GoodsReceiptDetailScreen(
                receiptId = id,
                onBack = { nav.popOnce(entry) },
                onCompleted = { nav.popOnce(entry) },
            )
        }
        composable(Routes.INVENTORY) { entry ->
            FeatureScaffold(stringResource(R.string.core_screen_inventory), onBack = { nav.popOnce(entry) }) { InventoryScreen() }
        }
        composable(Routes.REPORT) { entry ->
            FeatureScaffold(stringResource(R.string.core_screen_report), onBack = { nav.popOnce(entry) }) { ReportScreen() }
        }

        // ----- Khách hàng (Phase 1) -----
        composable(Routes.CUSTOMERS) { entry ->
            CustomerListScreen(
                onBack = { nav.popOnce(entry) },
                onOpenDetail = { nav.navigateOnce(entry, Routes.customerDetail(it)) },
                onAdd = { nav.navigateOnce(entry, Routes.CUSTOMER_ADD) },
            )
        }
        composable(
            Routes.CUSTOMER_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            CustomerDetailScreen(customerId = id, onBack = { nav.popOnce(entry) })
        }
        composable(Routes.CUSTOMER_ADD) { entry ->
            AddCustomerScreen(
                onCreated = { nav.popOnce(entry) },
                onCancel = { nav.popOnce(entry) },
            )
        }

        composable(Routes.PRODUCTS) { entry ->
            ProductListScreen(
                onBack = { nav.popOnce(entry) },
                onOpenDetail = { nav.navigateOnce(entry, Routes.productDetail(it)) },
                onAdd = { nav.navigateOnce(entry, Routes.PRODUCT_ADD) },
            )
        }
        composable(
            Routes.PRODUCT_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            ProductDetailScreen(productId = id, onBack = { nav.popOnce(entry) })
        }
        composable(Routes.PRODUCT_ADD) { entry ->
            AddProductScreen(onCreated = { nav.popOnce(entry) }, onCancel = { nav.popOnce(entry) })
        }
        composable(Routes.INVOICE_HISTORY) { entry ->
            FeatureScaffold(stringResource(R.string.core_screen_invoices), onBack = { nav.popOnce(entry) }) { InvoiceListScreen() }
        }
        composable(Routes.RETURNS) { entry ->
            FeatureScaffold(stringResource(R.string.core_screen_returns), onBack = { nav.popOnce(entry) }) {
                ReturnsScreen(onOpenReturn = { nav.navigateOnce(entry, Routes.returnNew(it)) })
            }
        }
        composable(
            Routes.RETURN_NEW,
            arguments = listOf(navArgument("invoiceId") { type = NavType.LongType }),
        ) { entry ->
            val invId = entry.arguments?.getLong("invoiceId") ?: 0L
            ReturnFormScreen(
                invoiceId = invId,
                onBack = { nav.popOnce(entry) },
                onDone = { nav.popOnce(entry) },
            )
        }
        composable(Routes.CHANGE_PASSWORD) { entry ->
            ChangePasswordScreen(onBack = { nav.popOnce(entry) }, onDone = { nav.popOnce(entry) })
        }

        // ----- Nhà cung cấp (Phase B) -----
        composable(Routes.SUPPLIERS) { entry ->
            SupplierListScreen(
                onBack = { nav.popOnce(entry) },
                onAdd = { nav.navigateOnce(entry, Routes.SUPPLIER_ADD) },
                onEdit = { nav.navigateOnce(entry, Routes.supplierEdit(it)) },
            )
        }
        composable(Routes.SUPPLIER_ADD) { entry ->
            AddSupplierScreen(onSaved = { nav.popOnce(entry) }, onCancel = { nav.popOnce(entry) })
        }
        composable(
            Routes.SUPPLIER_EDIT,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            AddSupplierScreen(supplierId = id, onSaved = { nav.popOnce(entry) }, onCancel = { nav.popOnce(entry) })
        }
    }
}

/**
 * Chống double-tap/đụng back cứng làm pop quá HUB → màn trắng.
 * Chỉ thực hiện điều hướng khi entry nguồn còn RESUMED (chưa bắt đầu transition trước đó).
 */
private fun NavBackStackEntry.isResumed() = lifecycle.currentState == Lifecycle.State.RESUMED

private fun NavController.popOnce(from: NavBackStackEntry) {
    if (from.isResumed()) popBackStack()
}

private fun NavController.navigateOnce(from: NavBackStackEntry, route: String) {
    if (from.isResumed()) navigate(route)
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
