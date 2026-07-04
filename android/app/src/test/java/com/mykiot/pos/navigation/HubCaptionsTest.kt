package com.mykiot.pos.navigation

import com.mykiot.pos.R
import com.mykiot.pos.core.i18n.FakeResProvider
import com.mykiot.pos.core.network.dto.HubSummaryDto
import org.junit.Assert.assertEquals
import org.junit.Test

class HubCaptionsTest {
    private val res = FakeResProvider()
    private val summary = HubSummaryDto(
        totalProducts = 1234,
        lowStockCount = 12,
        outOfStockCount = 0,
        totalCustomers = 87,
        totalSuppliers = 15,
        draftReceiptsCount = 3,
    )

    @Test fun `ton kho null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_fallback),
            captionFor(Routes.INVENTORY, null, res),
        )

    @Test fun `ton kho het hang uu tien hon sap het`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_out, 2),
            captionFor(Routes.INVENTORY, summary.copy(outOfStockCount = 2, lowStockCount = 5), res),
        )

    @Test fun `ton kho sap het khi out la 0`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_low, 12),
            captionFor(Routes.INVENTORY, summary, res),
        )

    @Test fun `ton kho du hang khi ca hai deu 0`() =
        assertEquals(
            res.get(R.string.core_hub_caption_inventory_ok),
            captionFor(Routes.INVENTORY, summary.copy(lowStockCount = 0, outOfStockCount = 0), res),
        )

    @Test fun `san pham co so lieu dung total va low stock`() =
        assertEquals(
            res.get(R.string.core_hub_caption_products, "1.234", 12),
            captionFor(Routes.PRODUCTS, summary, res),
        )

    @Test fun `san pham null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_products_fallback),
            captionFor(Routes.PRODUCTS, null, res),
        )

    @Test fun `khach hang co so lieu`() =
        assertEquals(
            res.get(R.string.core_hub_caption_customers, 87),
            captionFor(Routes.CUSTOMERS, summary, res),
        )

    @Test fun `khach hang null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_customers_fallback),
            captionFor(Routes.CUSTOMERS, null, res),
        )

    @Test fun `nha cung cap co so lieu`() =
        assertEquals(
            res.get(R.string.core_hub_caption_suppliers, 15),
            captionFor(Routes.SUPPLIERS, summary, res),
        )

    @Test fun `nha cung cap null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_suppliers_fallback),
            captionFor(Routes.SUPPLIERS, null, res),
        )

    @Test fun `nhap hang co so lieu phieu cho`() =
        assertEquals(
            res.get(R.string.core_hub_caption_receipt_draft, 3),
            captionFor(Routes.RECEIPT, summary, res),
        )

    @Test fun `nhap hang null summary dung fallback`() =
        assertEquals(
            res.get(R.string.core_hub_caption_receipt_fallback),
            captionFor(Routes.RECEIPT, null, res),
        )

    @Test fun `tra hang luon tinh bat ke summary`() {
        val expected = res.get(R.string.core_hub_caption_returns)
        assertEquals(expected, captionFor(Routes.RETURNS, null, res))
        assertEquals(expected, captionFor(Routes.RETURNS, summary, res))
    }

    @Test fun `nhom hang luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_categories), captionFor(Routes.CATEGORIES, summary, res))

    @Test fun `lich su nhap luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_receipt_history), captionFor(Routes.RECEIPT_HISTORY, summary, res))

    @Test fun `hoa don luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_invoices), captionFor(Routes.INVOICE_HISTORY, summary, res))

    @Test fun `bao cao luon tinh`() =
        assertEquals(res.get(R.string.core_hub_caption_report), captionFor(Routes.REPORT, summary, res))
}
