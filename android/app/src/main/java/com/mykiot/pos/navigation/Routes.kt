package com.mykiot.pos.navigation

object Routes {
    const val LOGIN = "login"
    const val HOME = "home"

    // Home inner nav (NavController trong HomeNavHost)
    const val HUB = "hub"                  // màn lưới chức năng (start destination)
    const val RECEIPT = "receipt"          // Nhập hàng (màn cũ, nay là destination)
    const val INVENTORY = "inventory"      // Tồn kho
    const val REPORT = "report"            // Báo cáo

    const val CUSTOMERS = "customers"
    const val CUSTOMER_DETAIL = "customer_detail/{id}"  // arg: id
    const val CUSTOMER_ADD = "customer_add"
    const val PRODUCTS = "products"
    const val PRODUCT_DETAIL = "product_detail/{id}"
    const val INVOICE_HISTORY = "invoice_history"
    const val INVOICE_DETAIL = "invoice_detail/{id}"
    const val RETURNS = "returns"
    const val RETURN_NEW = "return_new"
    const val CHANGE_PASSWORD = "change_password"

    fun customerDetail(id: Long) = "customer_detail/$id"
    fun productDetail(id: Long) = "product_detail/$id"
    fun invoiceDetail(id: Long) = "invoice_detail/$id"
}
