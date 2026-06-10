package com.mykiot.pos.core.auth

data class CurrentUser(
    val id: Long,
    val fullName: String,
    val role: String,    // "OWNER" | "CASHIER"
    val tenantId: Long,
    val tenantName: String,
)
