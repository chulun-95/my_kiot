package com.mykiot.pos.navigation

import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.dto.HubSummaryDto
import com.mykiot.pos.core.util.formatCount

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
