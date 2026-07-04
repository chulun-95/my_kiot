package com.mykiot.pos.navigation

import androidx.annotation.StringRes
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.AssignmentReturn
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.outlined.Assessment
import androidx.compose.material.icons.outlined.Category
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.LocalShipping
import androidx.compose.material.icons.outlined.Sell
import androidx.compose.ui.graphics.vector.ImageVector
import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.dto.HubSummaryDto
import com.mykiot.pos.core.util.formatCount

internal data class HubItem(
    @StringRes val label: Int,
    val route: String,
    val icon: ImageVector,
    val ownerOnly: Boolean = false,
)

internal data class HubGroup(@StringRes val title: Int, val items: List<HubItem>)

internal val hubGroups = listOf(
    HubGroup(
        R.string.core_hub_group_quick,
        listOf(
            HubItem(R.string.core_hub_inventory, Routes.INVENTORY, Icons.Outlined.Inventory2),
            HubItem(R.string.core_hub_receipt, Routes.RECEIPT, Icons.AutoMirrored.Outlined.ReceiptLong),
            HubItem(R.string.core_hub_products, Routes.PRODUCTS, Icons.Outlined.Sell),
            HubItem(R.string.core_hub_customers, Routes.CUSTOMERS, Icons.Outlined.Group),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_manage,
        listOf(
            HubItem(R.string.core_hub_suppliers, Routes.SUPPLIERS, Icons.Outlined.LocalShipping),
            HubItem(R.string.core_hub_categories, Routes.CATEGORIES, Icons.Outlined.Category),
            HubItem(R.string.core_hub_receipt_history, Routes.RECEIPT_HISTORY, Icons.Outlined.History),
            HubItem(R.string.core_hub_returns, Routes.RETURNS, Icons.AutoMirrored.Outlined.AssignmentReturn),
        ),
    ),
    HubGroup(
        R.string.core_hub_group_other,
        listOf(
            HubItem(R.string.core_hub_invoices, Routes.INVOICE_HISTORY, Icons.Outlined.Description),
            HubItem(R.string.core_hub_report, Routes.REPORT, Icons.Outlined.Assessment, ownerOnly = true),
        ),
    ),
)

/**
 * Dòng phụ hiển thị dưới tên mỗi card Hub. Số thật nếu [summary] có sẵn cho route đó
 * (out_of_stock ưu tiên hơn low_stock cho Tồn kho); ngược lại dùng caption tĩnh mô tả.
 * Vài route (Trả hàng, Nhóm hàng, Lịch sử nhập, Hóa đơn, Báo cáo) luôn tĩnh — không có
 * số liệu phù hợp (xem spec mục 2.5).
 */
fun captionFor(route: String, summary: HubSummaryDto?, res: ResProvider): String = when (route) {
    Routes.INVENTORY -> when {
        summary == null -> res.get(R.string.core_hub_caption_inventory_fallback)
        summary.outOfStockCount > 0 -> res.get(R.string.core_hub_caption_inventory_out, summary.outOfStockCount)
        summary.lowStockCount > 0 -> res.get(R.string.core_hub_caption_inventory_low, summary.lowStockCount)
        else -> res.get(R.string.core_hub_caption_inventory_ok)
    }
    Routes.PRODUCTS -> if (summary == null) {
        res.get(R.string.core_hub_caption_products_fallback)
    } else {
        res.get(R.string.core_hub_caption_products, formatCount(summary.totalProducts), summary.lowStockCount)
    }
    Routes.CUSTOMERS -> if (summary == null) {
        res.get(R.string.core_hub_caption_customers_fallback)
    } else {
        res.get(R.string.core_hub_caption_customers, summary.totalCustomers)
    }
    Routes.SUPPLIERS -> if (summary == null) {
        res.get(R.string.core_hub_caption_suppliers_fallback)
    } else {
        res.get(R.string.core_hub_caption_suppliers, summary.totalSuppliers)
    }
    Routes.RECEIPT -> if (summary == null) {
        res.get(R.string.core_hub_caption_receipt_fallback)
    } else {
        res.get(R.string.core_hub_caption_receipt_draft, summary.draftReceiptsCount)
    }
    Routes.RETURNS -> res.get(R.string.core_hub_caption_returns)
    Routes.CATEGORIES -> res.get(R.string.core_hub_caption_categories)
    Routes.RECEIPT_HISTORY -> res.get(R.string.core_hub_caption_receipt_history)
    Routes.INVOICE_HISTORY -> res.get(R.string.core_hub_caption_invoices)
    Routes.REPORT -> res.get(R.string.core_hub_caption_report)
    else -> ""
}
