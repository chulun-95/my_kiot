package com.mykiot.pos.navigation

object Routes {
    const val LOGIN = "login"
    const val HOME = "home"

    // Home inner nav (NavController trong HomeNavHost)
    const val HUB = "hub"                  // màn lưới chức năng (start destination)
    const val RECEIPT = "receipt"          // Nhập hàng (form tạo phiếu nháp)
    const val RECEIPT_DETAIL = "receipt_detail/{id}"  // Chi tiết phiếu nhập (hoàn tất)
    const val RECEIPT_HISTORY = "receipt_history"     // Lịch sử nhập
    const val INVENTORY = "inventory"      // Tồn kho
    const val REPORT = "report"            // Báo cáo

    const val CUSTOMERS = "customers"
    const val CUSTOMER_DETAIL = "customer_detail/{id}"  // arg: id
    const val CUSTOMER_ADD = "customer_add"
    const val PRODUCTS = "products"
    const val PRODUCT_DETAIL = "product_detail/{id}"
    const val PRODUCT_ADD = "product_add"
    const val PRODUCT_EDIT = "product_edit/{id}"
    const val INVOICE_HISTORY = "invoice_history"
    const val INVOICE_DETAIL = "invoice_detail/{id}"
    const val RETURNS = "returns"
    const val RETURN_NEW = "return_new/{invoiceId}"
    const val CHANGE_PASSWORD = "change_password"

    const val SUPPLIERS = "suppliers"
    const val SUPPLIER_ADD = "supplier_add"
    const val SUPPLIER_EDIT = "supplier_edit/{id}"
    const val CATEGORIES = "categories"

    fun receiptDetail(id: Long) = "receipt_detail/$id"
    fun customerDetail(id: Long) = "customer_detail/$id"
    fun productDetail(id: Long) = "product_detail/$id"
    fun productEdit(id: Long) = "product_edit/$id"
    fun invoiceDetail(id: Long) = "invoice_detail/$id"
    fun returnNew(invoiceId: Long) = "return_new/$invoiceId"
    fun supplierEdit(id: Long) = "supplier_edit/$id"
}
